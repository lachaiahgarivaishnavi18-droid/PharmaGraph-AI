import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlsplit

def cors_origins(environ=None):
    settings=os.environ if environ is None else environ
    production=settings.get('ENVIRONMENT')=='production'
    origin=settings.get('FRONTEND_URL','' if production else 'http://localhost:5173').rstrip('/')
    parsed=urlsplit(origin)
    if (not parsed.netloc or parsed.scheme not in ('http','https') or parsed.path or parsed.query or parsed.fragment
            or parsed.username or parsed.password or '*' in origin or production and parsed.scheme!='https'):
        raise RuntimeError('FRONTEND_URL must be an exact HTTPS origin in production')
    return [origin] if production else list(dict.fromkeys([origin,'http://localhost:5173','http://127.0.0.1:5173']))

def validate_host_storage(settings):
    if settings.get('DEPLOYMENT_TARGET')=='render-free':
        if not settings.get('DATABASE_URL','').startswith(('postgres://','postgresql://','postgresql+psycopg://')):
            raise RuntimeError('Render free hosting requires an external PostgreSQL DATABASE_URL; local SQLite is not durable')
        if settings.get('DOCUMENT_STORAGE')!='database':
            raise RuntimeError('Render free hosting requires DOCUMENT_STORAGE=database; local uploads are not durable')

load_dotenv()
validate_host_storage(os.environ)
ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv('STORAGE_PATH', str(ROOT / 'runtime')))
if not DATA.is_absolute(): DATA = ROOT / DATA
DATA.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATA / "pharmagraph.db"}')
if DATABASE_URL.startswith(('postgres://','postgresql://')):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL.split('://',1)[1]
if DATABASE_URL.startswith('sqlite:///') and not Path(DATABASE_URL[10:]).is_absolute():
    DATABASE_URL = 'sqlite:///' + str(ROOT / DATABASE_URL[10:])
secret_file = DATA / '.jwt-secret'
SECRET = os.getenv('JWT_SECRET') or os.getenv('SECRET_KEY')
if not SECRET:
    if os.getenv('ENVIRONMENT') == 'production':
        raise RuntimeError('JWT_SECRET is required in production')
    import secrets
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32))
    SECRET = secret_file.read_text().strip()
MAX_UPLOAD = int(os.getenv('MAX_UPLOAD_MB', '20')) * 1024 * 1024
