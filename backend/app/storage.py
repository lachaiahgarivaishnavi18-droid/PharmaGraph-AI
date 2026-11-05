"""Store uploads durably in SQL when a host has no persistent filesystem."""
import os
from .core import DATA
from .models import DocumentFile

def save_upload(db,document_id,raw):
    backend=os.getenv('DOCUMENT_STORAGE','filesystem')
    if backend=='database':
        db.add(DocumentFile(document_id=document_id,content=raw))
    elif backend=='filesystem':
        folder=DATA/'uploads';folder.mkdir(exist_ok=True)
        (folder/document_id).write_bytes(raw)
    else: raise ValueError('DOCUMENT_STORAGE must be filesystem or database')

def read_upload(db,document_id):
    stored=db.get(DocumentFile,document_id)
    if stored is not None:return bytes(stored.content)
    return (DATA/'uploads'/document_id).read_bytes()
