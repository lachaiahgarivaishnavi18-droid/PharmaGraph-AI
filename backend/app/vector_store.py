"""Optional durable FAISS index. SQL passage vectors remain authoritative."""
import hashlib, json, os, re
from pathlib import Path
from uuid import uuid4
import numpy as np
from .core import DATA, ROOT

def index_directory(owner_id):
    if not re.fullmatch(r'[a-f0-9]{32}',owner_id): raise ValueError('Invalid vector-index owner')
    root=Path(os.getenv('VECTOR_STORE_PATH',str(DATA/'vectors')))
    if not root.is_absolute(): root=ROOT/root
    folder=root/owner_id
    folder.mkdir(parents=True,exist_ok=True)
    return folder

def similarities(query,vectors,owner_id,passage_ids,model):
    matrix=np.ascontiguousarray(vectors,dtype='float32')
    if matrix.shape[1]!=len(query): raise ValueError('Embedding dimensions changed; reprocess documents')
    store=os.getenv('VECTOR_STORE','sqlite')
    if store=='sqlite': return matrix @ np.asarray(query,dtype='float32')
    if store!='faiss': raise ValueError('VECTOR_STORE must be sqlite or faiss')
    try:
        import faiss
    except ImportError as exc: raise ValueError('Install faiss-cpu or set VECTOR_STORE=sqlite') from exc
    digest=hashlib.sha256(model.encode()+'|'.join(passage_ids).encode()+matrix.tobytes()).hexdigest()
    folder=index_directory(owner_id);index_path=folder/(digest+'.faiss')
    if index_path.exists():
        index=faiss.read_index(str(index_path))
        if index.d!=matrix.shape[1] or index.ntotal!=len(passage_ids): raise ValueError('Corrupt vector index; remove the owner cache and rebuild')
    else:
        index=faiss.IndexFlatIP(matrix.shape[1]);index.add(matrix)
        temporary=folder/(uuid4().hex+'.tmp')
        faiss.write_index(index,str(temporary));temporary.replace(index_path)
        (folder/(digest+'.json')).write_text(json.dumps({'embedding_model':model,'passage_ids':passage_ids}))
    scores,indices=index.search(np.ascontiguousarray([query],dtype='float32'),len(passage_ids))
    ordered=np.zeros(len(passage_ids),dtype='float32')
    for score,idx in zip(scores[0],indices[0]):
        if idx>=0: ordered[idx]=score
    return ordered
