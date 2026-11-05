"""Administrative local CLI. No hidden demo account or fixed password."""
import argparse, getpass, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.models import Base,engine,Session,User,Document
from app.auth import hash_password
from app.ingestion import ingest,process
from app.graph import graph_data,sync_neo4j
from sqlalchemy import select

def main():
    parser=argparse.ArgumentParser(description='PharmaGraph AI database and ingestion commands')
    parser.add_argument('command',choices=['init','create-user','seed','ingest','reprocess','graph'])
    parser.add_argument('--email');parser.add_argument('--name',default='Researcher');parser.add_argument('--files',nargs='*')
    args=parser.parse_args();Base.metadata.create_all(engine)
    if args.command=='init': print('Database schema initialized.');return
    if not args.email: parser.error('--email is required')
    with Session() as db:
        user=db.scalar(select(User).where(User.email==args.email.lower()))
        if args.command=='create-user':
            if user: parser.error('User already exists')
            password=getpass.getpass('Password (at least 10 characters): ')
            if len(password)<10: parser.error('Password must be at least 10 characters')
            db.add(User(email=args.email.lower(),name=args.name,password=hash_password(password)));db.commit();print('User created.');return
        if not user: parser.error('User not found; create an account first')
        if args.command in ('seed','ingest'):
            paths=sorted((Path(__file__).resolve().parents[1]/'data'/'sample_documents').glob('*.txt')) if args.command=='seed' else [Path(p) for p in args.files or []]
            for path in paths:
                doc,duplicate=ingest(db,user.id,path.name,path.read_bytes())
                print(doc.id,doc.status,'duplicate' if duplicate else '',doc.error or '')
        elif args.command=='reprocess':
            for doc in db.scalars(select(Document).where(Document.owner_id==user.id)).all():
                result=process(db,doc);print(result.id,result.status,result.error or '')
        elif args.command=='graph': print(sync_neo4j(graph_data(db,user.id),user.id))

if __name__=='__main__':main()
