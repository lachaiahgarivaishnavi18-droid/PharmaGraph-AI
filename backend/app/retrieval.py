import math, re
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from .models import Chunk, Document
from .vectors import embed, cosine, MODEL
from .vector_store import similarities
from .graph import graph_data, neighborhood

def tokens(text): return [t for t in re.findall(r'[a-z0-9]+', text.lower()) if t not in ENGLISH_STOP_WORDS]

class Search(BaseModel):
    query: str = Field(min_length=1, max_length=3000)
    top_k: int = Field(default=8, ge=1, le=50)
    min_score: float = Field(default=0.03, ge=0, le=1)
    year_from: int | None = Field(default=None, ge=1500, le=2200)
    year_to: int | None = Field(default=None, ge=1500, le=2200)
    document_type: str | None = None
    document_ids: list[str] = Field(default_factory=list, max_length=100)
    entity_ids: list[str] = Field(default_factory=list, max_length=20)
    graph_hops: int = Field(default=1, ge=0, le=2)
    weights: dict[str,float] = Field(default_factory=lambda: {'vector':.4,'keyword':.25,'graph':.25,'metadata':.1})
    @model_validator(mode='after')
    def validate_weights(self):
        if set(self.weights) != {'vector','keyword','graph','metadata'} or any(not math.isfinite(v) or v < 0 for v in self.weights.values()) or sum(self.weights.values()) <= 0:
            raise ValueError('Provide nonnegative vector, keyword, graph and metadata weights with positive total')
        if self.year_from and self.year_to and self.year_from > self.year_to: raise ValueError('Invalid year range')
        return self

def bm25(query, texts):
    terms = tokens(query); corpus = [tokens(t) for t in texts]
    avg = sum(map(len, corpus)) / max(1, len(corpus)); scores=[]
    for doc in corpus:
        counts = Counter(doc); score=0
        for term in terms:
            df = sum(term in t for t in corpus)
            idf = math.log(1+(len(corpus)-df+.5)/(df+.5))
            tf=counts[term]
            score += idf*tf*2.5/(tf+1.5*(.25+.75*len(doc)/max(avg,1)))
        scores.append(score)
    return np.array(scores)

def retrieve(db, owner_id, request: Search, mode='hybrid'):
    rows = db.execute(select(Chunk,Document).join(Document).where(Document.owner_id == owner_id, Document.status == 'processed')).all()
    rows = [(c,d) for c,d in rows if (not request.document_ids or d.id in request.document_ids)
            and (not request.year_from or (d.meta.get('publication_year') or 0) >= request.year_from)
            and (not request.year_to or (d.meta.get('publication_year') or 9999) <= request.year_to)
            and (not request.document_type or request.document_type == d.meta.get('document_type'))]
    data = graph_data(db,owner_id)
    matched = [n for n in data['nodes'] if n['id'] in request.entity_ids or any(re.search(r'(?<!\w)' + re.escape(x) + r'(?!\w)',request.query,re.I) for x in [n['name'],*n['synonyms']])]
    ids = {n['id'] for n in matched}
    if request.graph_hops:
        for node in matched: ids.update(n['id'] for n in neighborhood(data,node['id'],request.graph_hops)['nodes'])
    edges = [e for e in data['edges'] if e['source'] in ids or e['target'] in ids]
    passages = {e['source_passage_id'] for e in edges}
    if request.entity_ids:
        from .models import Mention
        permitted = set(db.scalars(select(Mention.passage_id).where(Mention.entity_id.in_(request.entity_ids))))
        rows = [(c,d) for c,d in rows if c.id in permitted]
    if not rows: return {'results':[], 'graph_evidence':[], 'matched_entities':matched,'embedding_model':MODEL}
    if any(d.meta.get('embedding_model', 'local-hashing-v1') != MODEL for c,d in rows):
        from fastapi import HTTPException
        raise HTTPException(409, 'Embedding model changed. Reprocess your documents before retrieval.')
    # Expand with synonyms only; graph neighbors do not get promoted into the question.
    expanded = request.query + ' ' + ' '.join(alias for n in matched for alias in n['synonyms'])
    vectors = similarities(embed([expanded])[0], [c.vector for c,d in rows], owner_id, [c.id for c,d in rows], MODEL)
    keywords = bm25(expanded,[c.text for c,d in rows]); maximum = max(keywords.max(),1e-9)
    keywords_norm = keywords/maximum
    weights={k:v/sum(request.weights.values()) for k,v in request.weights.items()}
    results=[]
    for i,(chunk,doc) in enumerate(rows):
        # Hash collisions alone are not evidence of lexical relevance in offline mode.
        if MODEL == 'local-hashing-v1' and not (set(tokens(expanded)) & set(tokens(chunk.text))) and chunk.id not in passages:
            continue
        title = len(set(tokens(request.query)) & set(tokens(doc.title))) / max(1,len(set(tokens(request.query))))
        components={'vector':float(max(0,vectors[i])), 'keyword':float(keywords_norm[i]), 'graph':float(chunk.id in passages),'metadata':title}
        score = sum(components[k]*weights[k] for k in weights) if mode == 'hybrid' else components[{'semantic':'vector','keyword':'keyword','graph':'graph'}[mode]]
        if score < request.min_score or not any(components[k] > 0 for k in ('vector','keyword','graph')): continue
        results.append({'document_id':doc.id,'passage_id':chunk.id,'document_title':doc.title,'passage_text':chunk.text,'page_number':chunk.page,'section':chunk.section,
                        'doi':doc.meta.get('doi'),'pmid':doc.meta.get('pmid'),'publication_year':doc.meta.get('publication_year'),'document_type':doc.meta.get('document_type'),
                        'synthetic':doc.meta.get('synthetic',False),'score':round(score,6),'components':components,'bm25_raw':float(keywords[i]),'source_url':doc.meta.get('source_url')})
    results.sort(key=lambda r:r['score'],reverse=True)
    results=results[:request.top_k]; retrieved={r['passage_id'] for r in results}
    return {'results':results,'graph_evidence':[e for e in edges if e['source_passage_id'] in retrieved], 'matched_entities':matched,'embedding_model':MODEL}
