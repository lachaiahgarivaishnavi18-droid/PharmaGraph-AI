import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from alembic import context
from sqlalchemy import create_engine
from app.models import Base
from app.core import DATABASE_URL

def run():
    if context.is_offline_mode():
        context.configure(url=DATABASE_URL,target_metadata=Base.metadata,literal_binds=True)
        with context.begin_transaction(): context.run_migrations()
    else:
        engine=create_engine(DATABASE_URL)
        with engine.connect() as connection:
            context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
            with context.begin_transaction(): context.run_migrations()
run()
