from sqlalchemy import select
from app.models import Session,DocumentFile
from app.core import DATA
P='/api/v1'

def test_database_upload_survives_without_filesystem_and_can_reprocess(client,auth,monkeypatch):
    monkeypatch.setenv('DOCUMENT_STORAGE','database')
    raw=b'Title: Durable uploaded source\nYear: 2025\nDrug Aster inhibits Target Sigma. This is synthetic educational data.'
    response=client.post(P+'/documents/upload',headers=auth,files={'files':('durable.txt',raw)})
    assert response.status_code==200,response.text
    doc=response.json()['items'][0]
    assert doc['status']=='processed'
    assert not (DATA/'uploads'/doc['id']).exists()
    with Session() as db:
        assert db.get(DocumentFile,doc['id']).content==raw
    result=client.post(P+'/documents/'+doc['id']+'/process',headers=auth)
    assert result.status_code==200 and result.json()['status']=='processed'
    assert client.delete(P+'/documents/'+doc['id'],headers=auth).status_code==204
    with Session() as db:
        assert db.get(DocumentFile,doc['id']) is None

def test_database_demo_seed_is_idempotent(client,auth,monkeypatch):
    monkeypatch.setenv('DOCUMENT_STORAGE','database')
    first=client.post(P+'/demo/seed',headers=auth).json()['items']
    second=client.post(P+'/demo/seed',headers=auth).json()['items']
    assert len(first)==3 and all(d['status']=='processed' for d in first)
    assert all(d['duplicate'] for d in second)
    with Session() as db:assert len(db.scalars(select(DocumentFile)).all())==3
