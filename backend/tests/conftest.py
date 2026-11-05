import os, sys, tempfile
from pathlib import Path
import pytest

_directory=tempfile.TemporaryDirectory(prefix='pharmagraph-tests-')
os.environ['STORAGE_PATH']=_directory.name
os.environ['DATABASE_URL']='sqlite:///'+str(Path(_directory.name)/'test.db')
os.environ['JWT_SECRET']='test-only-key-not-for-production-123456789'
os.environ['RATE_LIMIT_PER_MINUTE']='10000'
os.environ['LLM_PROVIDER']='offline'
os.environ['EMBEDDING_MODEL']='local-hashing-v1'
os.environ['FRONTEND_URL']='https://pharmagraph-ai-nine.vercel.app'
os.environ.pop('LLM_API_KEY',None)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app, rate_buckets
from app.models import Base, engine
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    Base.metadata.drop_all(engine); rate_buckets.clear()
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope='session',autouse=True)
def close_test_database():
    yield
    engine.dispose()
    _directory.cleanup()

@pytest.fixture
def tmp_path():
    # Avoid scanning a machine-wide pytest directory outside this test run.
    with tempfile.TemporaryDirectory(prefix='case-',dir=_directory.name) as directory:
        yield Path(directory)

@pytest.fixture
def auth(client):
    result=client.post('/api/v1/auth/register',json={'name':'Test Researcher','email':'test@example.com','password':'secure-test-password'})
    assert result.status_code==201,result.text
    return {'Authorization':'Bearer '+result.json()['access_token']}

@pytest.fixture
def corpus(client,auth):
    response=client.post('/api/v1/demo/seed',headers=auth)
    assert response.status_code==200,response.text
    assert len(response.json()['items'])==3
    assert all(d['status']=='processed' for d in response.json()['items']),response.text
    return response.json()['items']
