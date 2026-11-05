import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from app.core import cors_origins,validate_host_storage
from app.auth import db_session
from app.main import app

ORIGIN='https://pharmagraph-ai-nine.vercel.app'
def test_production_cors_is_exact_and_rejects_wildcards():
    assert cors_origins({'ENVIRONMENT':'production','FRONTEND_URL':ORIGIN})==[ORIGIN]
    for value in ('*','https://*.vercel.app','http://localhost:5173',ORIGIN+'/app','',ORIGIN+'?test=1'):
        with pytest.raises(RuntimeError):cors_origins({'ENVIRONMENT':'production','FRONTEND_URL':value})

def test_browser_cors_preflight_allows_live_frontend_only(client):
    response=client.options('/api/v1/documents/upload',headers={'Origin':ORIGIN,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
    assert response.status_code==200
    assert response.headers['access-control-allow-origin']==ORIGIN
    rejected=client.options('/api/v1/documents/upload',headers={'Origin':'https://other.vercel.app','Access-Control-Request-Method':'POST'})
    assert rejected.status_code==400 and 'access-control-allow-origin' not in rejected.headers

def test_health_checks_database_and_keeps_private_routes_protected(client):
    health=client.get('/api/v1/health')
    assert health.status_code==200 and health.json()['database']=='ok'
    for path in ('/api/v1/documents','/api/v1/entities','/api/v1/graph','/api/v1/research/sessions'):
        assert client.get(path).status_code in (401,403)
    class UnavailableDatabase:
        def execute(self,*args):raise OperationalError('SELECT 1',{},Exception('offline'))
    def unavailable():yield UnavailableDatabase()
    app.dependency_overrides[db_session]=unavailable
    try:
        response=client.get('/api/v1/health')
        assert response.status_code==503 and response.json()=={'status':'unavailable','database':'unavailable'}
    finally:app.dependency_overrides.pop(db_session,None)

def test_render_free_rejects_ephemeral_database_and_uploads():
    for database,storage in [('sqlite:///local.db','database'),('postgresql://example/db','filesystem')]:
        with pytest.raises(RuntimeError):validate_host_storage({'DEPLOYMENT_TARGET':'render-free','DATABASE_URL':database,'DOCUMENT_STORAGE':storage})
    validate_host_storage({'DEPLOYMENT_TARGET':'render-free','DATABASE_URL':'postgresql+psycopg://example/db','DOCUMENT_STORAGE':'database'})
