import hashlib, secrets, hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .core import SECRET
from .models import Session, User

def db_session():
    with Session() as db:
        yield db

def hash_password(password):
    salt = secrets.token_hex(16)
    result = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600_000).hex()
    return f'{salt}${result}'

def verify(password, hashed):
    salt, result = hashed.split('$')
    return hmac.compare_digest(result, hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600_000).hex())

def token(user):
    return jwt.encode({'sub': user.id, 'exp': datetime.now(timezone.utc) + timedelta(hours=8), 'iat': datetime.now(timezone.utc)}, SECRET, algorithm='HS256')

def current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db=Depends(db_session)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=['HS256'], options={'require': ['exp', 'sub']})
        user = db.get(User, payload['sub'])
        if not user: raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, 'Invalid or expired authentication token')

def require_editor(user=Depends(current_user)):
    if user.role not in ('researcher', 'admin'): raise HTTPException(403, 'Researcher role required')
    return user
