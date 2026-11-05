"""Read-only official API connectors; never fetch user supplied URLs or full text."""
import time
import xml.etree.ElementTree as ET
from threading import Lock
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from .auth import current_user
router=APIRouter(prefix='/sources',dependencies=[Depends(current_user)])
_lock=Lock(); _last={}
def fetch(source,url,params):
    with _lock:
        delay=max(0,.4-(time.monotonic()-_last.get(source,0)))
        if delay: time.sleep(delay)
        _last[source]=time.monotonic()
    try:
        with httpx.Client(timeout=20,follow_redirects=False,headers={'User-Agent':'PharmaGraphAI/1.0 (literature research)'}) as client:
            response=client.get(url,params=params); response.raise_for_status()
        return response
    except httpx.HTTPError: raise HTTPException(502,f'{source} is unavailable or rate limited; retry later')
@router.get('/europe-pmc/search')
def europe(q:str=Query(min_length=2,max_length=500),page:int=Query(1,ge=1,le=100)):
    data=fetch('Europe PMC','https://www.ebi.ac.uk/europepmc/webservices/rest/search',{'query':q,'format':'json','resultType':'core','pageSize':20,'page':page}).json()
    return {'source':'Europe PMC','retrieved_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'access':'Metadata discovery only. Check each article license before importing full text.','data':data}
@router.get('/pubmed/search')
def pubmed(q:str=Query(min_length=2,max_length=500)):
    import os
    params={'db':'pubmed','term':q,'retmode':'json','retmax':20}
    if os.getenv('PUBMED_API_KEY'): params['api_key']=os.environ['PUBMED_API_KEY']
    return {'source':'PubMed','data':fetch('PubMed','https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',params).json()}
@router.get('/pubchem/compound/{identifier}')
def pubchem(identifier:str):
    if not identifier.isdigit() or len(identifier)>12: raise HTTPException(422,'Use a numeric PubChem CID')
    return {'source':'PubChem','data':fetch('PubChem',f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{identifier}/property/Title,MolecularFormula,MolecularWeight/JSON',{}).json()}
@router.get('/clinical-trials/search')
def trials(q:str=Query(min_length=2,max_length=500)):
    return {'source':'ClinicalTrials.gov','data':fetch('ClinicalTrials.gov','https://clinicaltrials.gov/api/v2/studies',{'query.term':q,'pageSize':20,'format':'json'}).json()}
@router.get('/uniprot/search')
def uniprot(q:str=Query(min_length=2,max_length=500)):
    return {'source':'UniProt','data':fetch('UniProt','https://rest.uniprot.org/uniprotkb/search',{'query':q,'format':'json','size':20}).json()}
