import io, json, logging, re, time
from collections import Counter, defaultdict, deque
from contextlib import asynccontextmanager
from typing import Annotated
from pathlib import Path
import networkx as nx
from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, delete, func, text as sql_text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .models import Base, engine, Session, User, Document, Chunk, Entity, Mention, Relation, ResearchSession, Message, Bookmark, Log, Audit, IngestionJob
from .auth import current_user, require_editor, db_session, hash_password, verify, token
from .core import DATA, MAX_UPLOAD, cors_origins
from .ingestion import ingest, process
from .graph import graph_data, network, neighborhood, sync_neo4j
from .retrieval import Search, retrieve
from .research import Ask, ask, validate_citations, find_conflicts
from .nlp import extract
from .vectors import MODEL
import os

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger('pharmagraph')
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield

app=FastAPI(title='PharmaGraph AI',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=cors_origins(),allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Authorization','Content-Type'])
rate_buckets=defaultdict(deque)
@app.middleware('http')
async def controls(request: Request, call_next):
    address=request.client.host if request.client else 'unknown'
    key=(address,'auth' if '/auth/' in request.url.path else 'general')
    bucket=rate_buckets[key]; now=time.monotonic()
    while bucket and bucket[0] < now-60: bucket.popleft()
    limit=20 if key[1]=='auth' else int(os.getenv('RATE_LIMIT_PER_MINUTE','180'))
    if len(bucket) >= limit: return JSONResponse({'detail':'Rate limit exceeded; retry in a minute'},status_code=429,headers={'Retry-After':'60'})
    bucket.append(now)
    # Reject oversized requests before multipart parsing (per-file check remains authoritative).
    if int(request.headers.get('content-length','0')) > MAX_UPLOAD*6:
        return JSONResponse({'detail':'Request exceeds upload limit'},status_code=413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    response.headers['X-Frame-Options']='DENY'
    return response

@app.exception_handler(Exception)
async def unexpected(request,exc):
    logger.exception('Request failed: %s',request.url.path,exc_info=exc)
    return JSONResponse({'detail':'The operation failed. Consult server logs.'},status_code=500)

api=APIRouter(prefix='/api/v1')
DB=Annotated[object,Depends(db_session)]
UserDep=Annotated[User,Depends(current_user)]
Editor=Annotated[User,Depends(require_editor)]

def owned(db, model, item_id, user):
    item=db.get(model,item_id)
    if not item or item.owner_id != user.id: raise HTTPException(404,'Record not found')
    return item
def doc_json(doc):
    return {'id':doc.id,'title':doc.title,'filename':doc.filename,'format':doc.format,'status':doc.status,'error':doc.error,'metadata':doc.meta,'upload_date':doc.created_at,'file_hash':doc.file_hash}
def chunk_json(c): return {'id':c.id,'document_id':c.document_id,'text':c.text,'page_number':c.page,'section':c.section,'ordinal':c.ordinal}
def entity_json(e): return {'id':e.id,'name':e.name,'original_name':e.original_name,'type':e.type,'synonyms':e.synonyms,'identifiers':e.identifiers}

class Register(BaseModel):
    name: str = Field(min_length=1,max_length=120)
    email: str = Field(min_length=5,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10,max_length=128)
class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
@api.post('/auth/register',status_code=201)
def register(body:Register,db:DB):
    user=User(name=body.name,email=body.email.lower().strip(),password=hash_password(body.password))
    db.add(user)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409,'Email is already registered')
    return {'access_token':token(user),'token_type':'bearer','user':{'id':user.id,'name':user.name,'email':user.email,'role':user.role}}
@api.post('/auth/login')
def login(body:Login,db:DB):
    user=db.scalar(select(User).where(User.email==body.email.lower().strip()))
    if not user or not verify(body.password,user.password): raise HTTPException(401,'Incorrect email or password')
    return {'access_token':token(user),'token_type':'bearer','user':{'id':user.id,'name':user.name,'email':user.email,'role':user.role}}
@api.get('/auth/me')
def me(user:UserDep): return {'id':user.id,'name':user.name,'email':user.email,'role':user.role}
@api.get('/health')
def health(db:DB):
    try: db.execute(sql_text('SELECT 1'))
    except SQLAlchemyError:
        return JSONResponse({'status':'unavailable','database':'unavailable'},status_code=503)
    return {'status':'ok','database':'ok','embedding_model':MODEL,'generation':'validated extracts','version':'1.0.0'}

@api.get('/documents')
def documents(db:DB,user:UserDep,q:str='',offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),year:int|None=None,document_type:str|None=None):
    docs=db.scalars(select(Document).where(Document.owner_id==user.id).order_by(Document.created_at.desc())).all()
    docs=[d for d in docs if q.lower() in (d.title+' '+json.dumps(d.meta)).lower() and (not year or d.meta.get('publication_year')==year) and (not document_type or d.meta.get('document_type')==document_type)]
    return {'items':[doc_json(d) for d in docs[offset:offset+limit]],'total':len(docs),'offset':offset,'limit':limit}
@api.get('/documents/export')
def export_documents(db:DB,user:UserDep):
    docs=db.scalars(select(Document).where(Document.owner_id==user.id)).all()
    return StreamingResponse(io.BytesIO(json.dumps([doc_json(d) for d in docs],indent=2).encode()),media_type='application/json',headers={'Content-Disposition':'attachment; filename="document-metadata.json"'})
@api.post('/documents/upload')
def upload(db:DB,user:Editor,files:list[UploadFile]=File(...)):
    if len(files)>5: raise HTTPException(400,'Upload at most five files per request')
    result=[]
    for f in files:
        raw=f.file.read(MAX_UPLOAD+1)
        if len(raw)>MAX_UPLOAD: raise HTTPException(413,'File exceeds upload size limit')
        doc,duplicate=ingest(db,user.id,f.filename,raw)
        result.append({**doc_json(doc),'duplicate':duplicate})
    return {'items':result}
@api.get('/documents/{document_id}')
def document(document_id:str,db:DB,user:UserDep):
    doc=owned(db,Document,document_id,user)
    jobs=db.scalars(select(IngestionJob).where(IngestionJob.document_id==doc.id).order_by(IngestionJob.created_at.desc())).all()
    return {**doc_json(doc),'ingestion_jobs':[{'id':j.id,'status':j.status,'stages':j.stages,'created_at':j.created_at} for j in jobs]}
@api.get('/documents/{document_id}/chunks')
def chunks(document_id:str,db:DB,user:UserDep):
    owned(db,Document,document_id,user)
    return {'items':[chunk_json(c) for c in db.scalars(select(Chunk).where(Chunk.document_id==document_id).order_by(Chunk.ordinal))]}
@api.delete('/documents/{document_id}',status_code=204)
def delete_document(document_id:str,db:DB,user:Editor):
    doc=owned(db,Document,document_id,user); db.delete(doc)
    db.add(Audit(owner_id=user.id,action='document.delete',object_id=document_id)); db.commit()
    (DATA/'uploads'/document_id).unlink(missing_ok=True)
@api.post('/documents/{document_id}/process')
def reprocess(document_id:str,db:DB,user:Editor): return doc_json(process(db,owned(db,Document,document_id,user)))

@api.get('/entities')
def entities(db:DB,user:UserDep,q:str='',type:str|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200)):
    items=db.scalars(select(Entity).where(Entity.owner_id==user.id).order_by(Entity.name)).all()
    items=[e for e in items if (q.lower() in (e.name+' '+ ' '.join(e.synonyms)).lower()) and (not type or e.type==type)]
    return {'items':[entity_json(e) for e in items[offset:offset+limit]],'total':len(items)}
class TextInput(BaseModel):
    text:str=Field(min_length=1,max_length=100000)
@api.post('/entities/extract')
def extract_entities(body:TextInput,db:DB,user:UserDep): return {'items':extract(body.text,db.scalars(select(Entity).where(Entity.owner_id==user.id)).all())}
class Normalize(BaseModel):
    name:str=Field(min_length=1,max_length=200)
@api.post('/entities/normalize')
def normalize(body:Normalize,db:DB,user:UserDep):
    matches=[e for e in db.scalars(select(Entity).where(Entity.owner_id==user.id)) if body.name.lower() in [e.name.lower(),*[s.lower() for s in e.synonyms]]]
    return {'items':[entity_json(e) for e in matches],'resolved':bool(matches)}
@api.get('/entities/{entity_id}')
def entity(entity_id:str,db:DB,user:UserDep):
    e=owned(db,Entity,entity_id,user)
    passages=db.execute(select(Chunk,Document).join(Document).join(Mention,Mention.passage_id==Chunk.id).where(Mention.entity_id==e.id,Document.owner_id==user.id)).all()
    return {**entity_json(e),'mentions':[{**chunk_json(c),'document_title':d.title,'metadata':d.meta} for c,d in passages]}
class EntityEdit(BaseModel):
    name:str=Field(min_length=1,max_length=200)
    type:str=Field(pattern=r'^(Drug|Compound|Disease|Target|Protein|Gene|Pathway|Mechanism|Clinical Trial|Adverse Event|Drug Class|Biological Process|Enzyme|Receptor|Dosage Form|API|Medical Condition)$')
    synonyms:list[str]=Field(default_factory=list,max_length=50)
    identifiers:dict[str,str]=Field(default_factory=dict)
@api.patch('/entities/{entity_id}')
def edit_entity(entity_id:str,body:EntityEdit,db:DB,user:Editor):
    e=owned(db,Entity,entity_id,user)
    for key,value in body.model_dump().items(): setattr(e,key,value)
    db.add(Audit(owner_id=user.id,action='entity.correct',object_id=e.id))
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409,'An entity with this name and type already exists')
    return entity_json(e)
@api.get('/entities/{entity_id}/relationships')
def entity_relations(entity_id:str,db:DB,user:UserDep):
    owned(db,Entity,entity_id,user)
    return neighborhood(graph_data(db,user.id),entity_id,1)

@api.post('/graph/build')
def build_graph(db:DB,user:Editor): return sync_neo4j(graph_data(db,user.id),user.id)
@api.get('/graph/stats')
def graph_stats(db:DB,user:UserDep):
    data=graph_data(db,user.id)
    return {'nodes':len(data['nodes']),'relationships':len(data['edges']),'distribution':dict(Counter(e['type'] for e in data['edges']))}
@api.get('/graph')
def graph(db:DB,user:UserDep,relationship_type:str|None=None,document_id:str|None=None,limit:int=Query(200,ge=1,le=1000)):
    data=graph_data(db,user.id)
    edges=[e for e in data['edges'] if (not relationship_type or e['type']==relationship_type) and (not document_id or e['source_document_id']==document_id)][:limit]
    ids={i for e in edges for i in (e['source'],e['target'])}
    nodes=([n for n in data['nodes'] if n['id'] in ids] if relationship_type or document_id else data['nodes'])[:limit]
    visible={n['id'] for n in nodes}
    return {'nodes':nodes,'edges':[e for e in edges if e['source'] in visible and e['target'] in visible]}
@api.get('/graph/entity/{entity_id}')
@api.get('/graph/related/{entity_id}')
def related(entity_id:str,db:DB,user:UserDep,hops:int=Query(1,ge=0,le=2)):
    owned(db,Entity,entity_id,user)
    return neighborhood(graph_data(db,user.id),entity_id,hops)
@api.get('/graph/paths')
def paths(source:str,target:str,db:DB,user:UserDep,hops:int=Query(3,ge=1,le=4)):
    owned(db,Entity,source,user); owned(db,Entity,target,user)
    data=graph_data(db,user.id); net=network(data).to_undirected()
    if source not in net or target not in net: return {'paths':[]}
    import itertools
    return {'paths':list(itertools.islice(nx.all_simple_paths(net,source,target,cutoff=hops),20)),'graph':data}
@api.get('/graph/evidence/{relationship_id}')
def edge_evidence(relationship_id:str,db:DB,user:UserDep):
    edge=next((e for e in graph_data(db,user.id)['edges'] if e['id']==relationship_id),None)
    if not edge: raise HTTPException(404,'Relationship not found')
    return edge

@api.post('/retrieval/{mode}')
def retrieval(mode:str,body:Search,db:DB,user:UserDep):
    if mode not in ('semantic','keyword','hybrid','graph'): raise HTTPException(404,'Unknown retrieval mode')
    return retrieve(db,user.id,body,mode)
@api.post('/research/ask')
@api.post('/research/summarize')
def research(body:Ask,db:DB,user:UserDep):
    if body.session_id: session=owned(db,ResearchSession,body.session_id,user)
    else:
        session=ResearchSession(owner_id=user.id,title=body.query[:150]); db.add(session); db.commit()
    response=ask(db,user.id,body)
    db.add(Message(session_id=session.id,question=body.query,response=response)); db.commit()
    return {**response,'session_id':session.id}
class Comparison(BaseModel):
    left:str=Field(min_length=1,max_length=200)
    right:str=Field(min_length=1,max_length=200)
@api.post('/research/compare')
def compare(body:Comparison,db:DB,user:UserDep):
    entities=db.scalars(select(Entity).where(Entity.owner_id==user.id)).all()
    def question(topic):
        ids=[e.id for e in entities if any(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',topic,re.I) for term in [e.name,*e.synonyms])]
        return Ask(query=topic,entity_ids=ids)
    return {'left':ask(db,user.id,question(body.left)),'right':ask(db,user.id,question(body.right)), 'limitations':['Side-by-side retrieved evidence does not establish comparative efficacy or safety.']}
@api.post('/research/conflicts')
def conflicts(body:Search,db:DB,user:UserDep):
    evidence=retrieve(db,user.id,body)
    return {'conflicts':find_conflicts(evidence['graph_evidence']),'retrieval':evidence,'limitations':['Only explicit positive/negative relationships are compared. Different models and outcomes can explain apparent contradictions.']}
class EvidenceCheck(BaseModel):
    query:Search
    response:dict
@api.post('/research/evidence-check')
def evidence_check(body:EvidenceCheck,db:DB,user:UserDep):
    retrieved=retrieve(db,user.id,body.query)
    issues=validate_citations(body.response,retrieved['results'],retrieved['graph_evidence'])
    return {'valid':not issues,'issues':issues,'limitations':'Exact excerpts and identifiers are checked; general semantic entailment is not established.'}

class SessionInput(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    topic:str=Field(default='General research',max_length=200)
@api.get('/research/sessions')
def sessions(db:DB,user:UserDep):
    return {'items':[{'id':s.id,'title':s.title,'topic':s.topic,'created_at':s.created_at} for s in db.scalars(select(ResearchSession).where(ResearchSession.owner_id==user.id).order_by(ResearchSession.created_at.desc()))]}
@api.post('/research/sessions')
def new_session(body:SessionInput,db:DB,user:UserDep):
    s=ResearchSession(owner_id=user.id,**body.model_dump()); db.add(s); db.commit()
    return {'id':s.id,'title':s.title,'topic':s.topic}
@api.get('/research/sessions/{session_id}')
def session(session_id:str,db:DB,user:UserDep):
    s=owned(db,ResearchSession,session_id,user)
    return {'id':s.id,'title':s.title,'topic':s.topic,'messages':[{'id':m.id,'question':m.question,'response':m.response,'created_at':m.created_at} for m in db.scalars(select(Message).where(Message.session_id==s.id).order_by(Message.created_at))]}
class BookmarkInput(BaseModel):
    passage_id:str
    note:str=Field(default='',max_length=3000)
@api.post('/research/bookmarks')
def bookmark(body:BookmarkInput,db:DB,user:UserDep):
    c=db.get(Chunk,body.passage_id)
    if not c: raise HTTPException(404,'Passage not found')
    owned(db,Document,c.document_id,user)
    mark=Bookmark(owner_id=user.id,**body.model_dump()); db.add(mark); db.commit()
    return {'id':mark.id}
@api.get('/research/bookmarks')
def bookmarks(db:DB,user:UserDep):
    rows=db.execute(select(Bookmark,Chunk,Document).join(Chunk,Bookmark.passage_id==Chunk.id).join(Document).where(Bookmark.owner_id==user.id)).all()
    return {'items':[{'id':b.id,'note':b.note,'passage':chunk_json(c),'document_title':d.title} for b,c,d in rows]}
@api.delete('/research/bookmarks/{bookmark_id}',status_code=204)
def remove_bookmark(bookmark_id:str,db:DB,user:UserDep):
    db.delete(owned(db,Bookmark,bookmark_id,user)); db.commit()
@api.get('/agents/logs')
def logs(db:DB,user:UserDep,offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500)):
    rows=db.scalars(select(Log).where(Log.owner_id==user.id).order_by(Log.created_at.desc()).offset(offset).limit(limit))
    return {'items':[{'id':l.id,'run_id':l.run_id,'agent':l.agent,'details':l.details,'duration_ms':l.duration_ms,'created_at':l.created_at} for l in rows]}

def analytics(db,user):
    docs=db.scalars(select(Document).where(Document.owner_id==user.id)).all()
    data=graph_data(db,user.id)
    messages=db.scalars(select(Message).join(ResearchSession).where(ResearchSession.owner_id==user.id)).all()
    count=db.scalar(select(func.count()).select_from(Chunk).join(Document).where(Document.owner_id==user.id,Document.status=='processed'))
    def distribution(values): return [{'name':str(k),'value':v} for k,v in Counter(values).items()]
    return {'documents':len(docs),'processed':sum(d.status=='processed' for d in docs),'failed':sum(d.status=='failed' for d in docs),'entities':len(data['nodes']),
            'nodes':len(data['nodes']),'relationships':len(data['edges']),'passages':count,'queries':len(messages),'grounded_responses':sum(bool(m.response.get('supporting_evidence')) for m in messages),
            'by_year':distribution(d.meta.get('publication_year') or 'Unknown' for d in docs),'by_type':distribution(d.meta.get('document_type','Unclassified') for d in docs),
            'by_entity':distribution(n['type'] for n in data['nodes']),'by_relationship':distribution(e['type'] for e in data['edges']), 'by_status':distribution(d.status for d in docs),
            'activity':distribution(m.created_at[:10] for m in messages),'recent_documents':[doc_json(d) for d in sorted(docs,key=lambda d:d.created_at,reverse=True)[:5]],
            'synthetic_documents':sum(bool(d.meta.get('synthetic')) for d in docs),'embedding_model':MODEL,
            'most_researched':distribution(n['name'] for m in messages for n in m.response.get('retrieval',{}).get('matched_entities',[]))}
@api.get('/analytics/{category}')
def dashboard(category:str,db:DB,user:UserDep):
    if category not in ('dashboard','documents','entities','graph','retrieval'): raise HTTPException(404,'Unknown analytics category')
    return analytics(db,user)

@api.post('/demo/seed')
def seed(db:DB,user:Editor):
    folder=Path(__file__).resolve().parents[2]/'data'/'sample_documents'
    # Repository-root data is also supported in development.
    if not folder.exists(): folder=Path(__file__).resolve().parents[2].parent/'data'/'sample_documents'
    result=[]
    for path in sorted(folder.glob('*.txt')):
        d,dup=ingest(db,user.id,path.name,path.read_bytes()); result.append({**doc_json(d),'duplicate':dup})
    return {'items':result}

from .sources import router as sources_router
api.include_router(sources_router)
app.include_router(api)
