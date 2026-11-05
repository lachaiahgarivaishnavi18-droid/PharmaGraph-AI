"""Initialize a mounted storage directory, then run the API as an unprivileged user."""
import os
from pathlib import Path

storage=Path(os.getenv('STORAGE_PATH','/app/runtime')).resolve()
storage.mkdir(parents=True,exist_ok=True)
if hasattr(os,'geteuid') and os.geteuid()==0:
    # Hosting volumes arrive root-owned. Only change the mount directory itself.
    os.chown(storage,10001,10001)
    os.chmod(storage,0o700)
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
os.umask(0o077)
port=int(os.getenv('PORT','8000'))
if not 1<=port<=65535: raise ValueError('Invalid PORT')
os.execvp('uvicorn',['uvicorn','app.main:app','--host','0.0.0.0','--port',str(port),'--workers','1'])
