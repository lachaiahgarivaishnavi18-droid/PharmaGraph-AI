"""Stateless offline hashing vectors; optional true SentenceTransformer embeddings."""
import os
from functools import lru_cache
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

MODEL = os.getenv('EMBEDDING_MODEL', 'local-hashing-v1')
@lru_cache(maxsize=1)
def transformer():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL, local_files_only=os.getenv('MODEL_DOWNLOADS','false').lower() != 'true')

def embed(texts):
    if MODEL != 'local-hashing-v1':
        return transformer().encode(texts, normalize_embeddings=True)
    return HashingVectorizer(n_features=512, alternate_sign=False, norm='l2', stop_words='english', ngram_range=(1,2)).transform(texts).toarray()

def cosine(query, vectors):
    if not vectors: return np.array([])
    matrix = np.array(vectors)
    if matrix.shape[1] != len(query): raise ValueError('Embedding model changed: reprocess documents before retrieval')
    return matrix @ query
