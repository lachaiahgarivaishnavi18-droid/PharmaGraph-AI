import json
import httpx
from app import sources, research
from app.research import validate_citations
from app.models import Session, User
from sqlalchemy import select

P='/api/v1'
def test_source_connectors_are_fixed_official_urls_and_validate_ids(client,auth,monkeypatch):
    calls=[]
    def fake(source,url,params):
        calls.append((source,url,params))
        return httpx.Response(200,json={'results':[]},request=httpx.Request('GET',url))
    monkeypatch.setattr(sources,'fetch',fake)
    for provider in ('pubmed','europe-pmc','clinical-trials','uniprot'):
        response=client.get(P+f'/sources/{provider}/search',params={'q':'Target Sigma'},headers=auth)
        assert response.status_code==200,response.text
    assert client.get(P+'/sources/pubchem/compound/123',headers=auth).status_code==200
    assert client.get(P+'/sources/pubchem/compound/not-a-cid',headers=auth).status_code==422
    assert client.get(P+'/sources/europe-pmc/search?q=x',headers=auth).status_code==422
    assert len(calls)==5 and all(url.startswith('https://') for _,url,_ in calls)
    assert {httpx.URL(url).host for _,url,_ in calls}=={'eutils.ncbi.nlm.nih.gov','www.ebi.ac.uk','clinicaltrials.gov','rest.uniprot.org','pubchem.ncbi.nlm.nih.gov'}

def test_provider_fabricated_quotes_fall_back_to_validated_excerpts(client,auth,corpus,monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {'choices':[{'message':{'content':json.dumps({'selections':[{'passage_id':'invented-id','quote':'Invented clinical claim.'}]})}}]}
    class FakeClient:
        def __init__(self,**kwargs): pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):return FakeResponse()
    monkeypatch.setenv('LLM_PROVIDER','openai-compatible');monkeypatch.setenv('LLM_API_KEY','test-only-not-a-real-key')
    monkeypatch.setattr(research.httpx,'Client',FakeClient)
    response=client.post(P+'/research/ask',headers=auth,json={'query':'Drug Aster Target Sigma'})
    assert response.status_code==200,response.text
    data=response.json()
    assert data['generation_mode']=='deterministic-extractive'
    assert data['citation_validation']['valid']
    assert all('Invented clinical claim.' not in e['quote_or_excerpt'] for e in data['supporting_evidence'])
    assert any('Provider unavailable' in l for l in data['evidence_limitations'])

def test_evidence_check_rejects_unchecked_narrative_and_graph(client,auth,corpus):
    result=client.post(P+'/research/ask',headers=auth,json={'query':'Drug Aster Target Sigma'}).json()
    result['answer']='This treatment is clinically effective.'
    result['graph_evidence']=[{'id':'fabricated','source':'fake','target':'fake'}]
    checked=client.post(P+'/research/evidence-check',headers=auth,json={'query':{'query':'Drug Aster Target Sigma'},'response':result}).json()
    assert not checked['valid']
    assert any('narrative' in issue for issue in checked['issues']) and any('Graph evidence' in issue for issue in checked['issues'])

def test_viewer_role_cannot_upload_or_delete(client,auth,corpus):
    with Session() as db:
        user=db.scalar(select(User).where(User.email=='test@example.com'));user.role='viewer';db.commit()
    assert client.get(P+'/documents',headers=auth).status_code==200
    assert client.post(P+'/documents/upload',headers=auth,files={'files':('a.txt',b'This is a sufficiently long document.')}).status_code==403
    assert client.delete(P+'/documents/'+corpus[0]['id'],headers=auth).status_code==403

def test_upload_bounds_and_unauthorized_bookmark(client,auth,corpus,monkeypatch):
    import app.main as main
    monkeypatch.setattr(main,'MAX_UPLOAD',64)
    assert client.post(P+'/documents/upload',headers=auth,files={'files':('large.txt',b'x'*500)}).status_code==413
    assert client.post(P+'/research/bookmarks',headers=auth,json={'passage_id':'unknown'}).status_code==404

def test_unrelated_query_abstains_with_a_populated_corpus(client,auth,corpus):
    result=client.post(P+'/research/ask',headers=auth,json={'query':'What is the astrophysical quasar neutrino entanglement?'}).json()
    assert not result['supporting_evidence'] and 'Insufficient evidence' in result['answer']

def test_faiss_index_matches_sql_vectors_and_persists(client,auth,corpus,monkeypatch,tmp_path):
    import pytest
    pytest.importorskip('faiss')
    monkeypatch.setenv('VECTOR_STORE','sqlite')
    expected=client.post(P+'/retrieval/hybrid',headers=auth,json={'query':'Drug Aster Target Sigma'}).json()['results']
    monkeypatch.setenv('VECTOR_STORE','faiss');monkeypatch.setenv('VECTOR_STORE_PATH',str(tmp_path))
    actual=client.post(P+'/retrieval/hybrid',headers=auth,json={'query':'Drug Aster Target Sigma'}).json()['results']
    assert [(r['passage_id'],r['score']) for r in actual]==[(r['passage_id'],r['score']) for r in expected]
    assert list(tmp_path.glob('*/*.faiss')) and list(tmp_path.glob('*/*.json'))
    cached=client.post(P+'/retrieval/hybrid',headers=auth,json={'query':'Drug Aster Target Sigma'}).json()['results']
    assert cached==actual
