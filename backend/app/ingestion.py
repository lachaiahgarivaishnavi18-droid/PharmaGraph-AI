import csv, hashlib, io, json, re, zipfile
from pathlib import Path
from sqlalchemy import select, delete
from fastapi import HTTPException
from .core import DATA
from .models import Document, Chunk, IngestionJob, Audit
from .nlp import populate
from .vectors import embed, MODEL
from .storage import save_upload, read_upload

FORMATS = {'pdf','txt','docx','csv','json','html','htm'}

def extract_pages(raw, extension):
    if extension == 'pdf':
        import fitz
        if not raw.startswith(b'%PDF-'): raise ValueError('File is not a valid PDF')
        with fitz.open(stream=raw, filetype='pdf') as pdf:
            if pdf.is_encrypted: raise ValueError('Encrypted PDFs are unsupported')
            return [(i+1, page.get_text(sort=True)) for i, page in enumerate(pdf)]
    if extension == 'docx':
        from docx import Document as Word
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if sum(x.file_size for x in archive.infolist()) > 100_000_000: raise ValueError('Expanded DOCX is too large')
        doc = Word(io.BytesIO(raw))
        return [(None, '\n'.join([p.text for p in doc.paragraphs] + [' | '.join(c.text for c in r.cells) for t in doc.tables for r in t.rows]))]
    text = raw.decode('utf-8-sig')
    if extension == 'json': text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    if extension == 'csv': text = '\n'.join(' | '.join(row) for row in csv.reader(io.StringIO(text)))
    if extension in ('html','htm'):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, 'html.parser')
        for tag in soup(['script','style','iframe','noscript']): tag.decompose()
        text = soup.get_text('\n')
    return [(None, text)]

def metadata(text, title):
    def field(name):
        match = re.search(r'^' + name + r':\s*(.+)$', text, re.I | re.M)
        return match[1].strip() if match else None
    doi = re.search(r'\b10\.\d{4,9}/[^\s<>"\]]+', text)
    pmid = re.search(r'PMID\s*:?\s*(\d+)', text, re.I)
    year = field('Year') or field('Publication year')
    return {'title': field('Title') or title, 'authors': (field('Authors') or '').split(';') if field('Authors') else [],
            'publication_year': int(year) if year and year.isdigit() and 1500 <= int(year) <= 2200 else None,
            'journal': field('Journal'), 'doi': doi[0].rstrip('.,;)') if doi else None, 'pmid': pmid[1] if pmid else None,
            'source_url': field('Source URL'), 'license_or_access_information': field('License') or 'User supplied; rights not independently verified',
            'abstract': field('Abstract'), 'document_type': field('Study type') or 'Unclassified',
            'synthetic': bool(re.search(r'\bSYNTHETIC EDUCATIONAL\b', text, re.I)), 'keywords': (field('Keywords') or '').split(','),
            'references': text.split('References\n')[-1][:10000] if 'References\n' in text else None}

def embedded_metadata(raw,extension):
    """Use explicit file properties only; creation dates are not publication dates."""
    if extension=='pdf':
        import fitz
        with fitz.open(stream=raw,filetype='pdf') as pdf:
            props=pdf.metadata or {}
            return {'title':props.get('title'),'authors':[props['author']] if props.get('author') else []}
    if extension=='docx':
        from docx import Document as Word
        props=Word(io.BytesIO(raw)).core_properties
        return {'title':props.title,'authors':[props.author] if props.author else []}
    if extension=='json':
        obj=json.loads(raw.decode('utf-8-sig'))
        if not isinstance(obj,dict): return {}
        source=obj.get('metadata',obj)
        if not isinstance(source,dict): return {}
        result={k:source[k] for k in ('title','abstract','journal','doi','pmid','source_url','license_or_access_information','document_type') if isinstance(source.get(k),str)}
        if isinstance(source.get('authors'),list) and all(isinstance(x,str) for x in source['authors']): result['authors']=source['authors']
        year=source.get('publication_year')
        if isinstance(year,int) and 1500<=year<=2200: result['publication_year']=year
        return result
    return {}

def chunk_pages(pages):
    result = []
    section = 'Body'
    for page, text in pages:
        buffer = []
        for line in text.splitlines():
            cleaned = ' '.join(line.replace('\x00','').split())
            if re.fullmatch(r'(abstract|introduction|methods|results|discussion|conclusion|conclusions|references|limitations)', cleaned, re.I):
                if buffer: result.append((page, section, ' '.join(buffer))); buffer = []
                section = cleaned.title()
            elif cleaned:
                buffer.append(cleaned)
        if buffer: result.append((page, section, ' '.join(buffer)))
    chunks = []
    for page, section, text in result:
        words = text.split()
        for start in range(0, len(words), 220):
            chunks.append((page, section, ' '.join(words[start:start+260])))
    return chunks

def process(db, doc):
    doc.status = 'processing'; doc.error = None
    job = IngestionJob(document_id=doc.id, status='processing', stages=['validate'])
    db.add(job); db.commit()
    try:
        raw = read_upload(db,doc.id)
        pages = extract_pages(raw, doc.format)
        text = '\n'.join(t for _,t in pages)
        if len(text.strip()) < 25: raise ValueError('No extractable text. Scanned PDFs require OCR before upload.')
        meta = metadata(text, doc.filename)
        embedded=embedded_metadata(raw,doc.format)
        for key,value in embedded.items():
            if value and (not meta.get(key) or key=='title' and meta[key]==doc.filename or key=='document_type' and meta[key]=='Unclassified'):
                meta[key]=value
        meta['embedding_model'] = MODEL
        for other in db.scalars(select(Document).where(Document.owner_id == doc.owner_id, Document.id != doc.id)):
            if any(meta.get(k) and meta[k] == other.meta.get(k) for k in ('doi','pmid')):
                raise ValueError(f'Duplicate DOI/PMID: document {other.id}')
        # Changes are transactional: a failed reprocess restores the previous passage set.
        db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
        chunks = [Chunk(document_id=doc.id, ordinal=i, page=p, section=s, text=t, vector=embed([t])[0].tolist()) for i,(p,s,t) in enumerate(chunk_pages(pages))]
        db.add_all(chunks); db.flush()
        populate(db, doc.owner_id, chunks)
        doc.meta = meta; doc.title = meta['title']; doc.status = 'processed'
        job.status = 'complete'; job.stages = ['validate','extract','metadata','sections','chunk','entities','embeddings','graph','complete']
        db.add(Audit(owner_id=doc.owner_id, action='document.process', object_id=doc.id)); db.commit()
    except Exception as exc:
        db.rollback()
        doc = db.get(Document, doc.id); doc.status = 'failed'; doc.error = str(exc)[:1000]
        job = db.get(IngestionJob, job.id); job.status = 'failed'; job.stages = [*job.stages, str(exc)[:500]]
        db.commit()
    return doc

def ingest(db, owner_id, filename, raw):
    extension = Path(filename or '').suffix.lower().lstrip('.')
    if extension not in FORMATS: raise HTTPException(415, 'Supported formats: PDF, TXT, DOCX, CSV, JSON, HTML')
    digest = hashlib.sha256(raw).hexdigest()
    duplicate = db.scalar(select(Document).where(Document.owner_id == owner_id, Document.file_hash == digest))
    if duplicate: return duplicate, True
    doc = Document(owner_id=owner_id, title=Path(filename).name, filename=Path(filename).name, format=extension, file_hash=digest)
    db.add(doc); db.flush()
    save_upload(db,doc.id,raw)
    db.commit()
    return process(db, doc), False
