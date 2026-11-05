from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, Text, ForeignKey, JSON, UniqueConstraint, event, LargeBinary
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .core import DATABASE_URL

def uid(): return uuid4().hex
def now(): return datetime.now(timezone.utc).isoformat()
class Base(DeclarativeBase): pass
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {})
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _): connection.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine, expire_on_commit=False)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='researcher')

class Document(Base):
    __tablename__ = 'research_documents'
    __table_args__ = (UniqueConstraint('owner_id', 'file_hash'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(Text)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(40), default=now)

class DocumentFile(Base):
    __tablename__ = 'document_files'
    document_id: Mapped[str] = mapped_column(ForeignKey('research_documents.id', ondelete='CASCADE'), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)

class Chunk(Base):
    __tablename__ = 'document_chunks'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey('research_documents.id', ondelete='CASCADE'), index=True)
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(nullable=True)
    section: Mapped[str] = mapped_column(String(100), default='Body')
    ordinal: Mapped[int]
    vector: Mapped[list] = mapped_column(JSON, default=list)

class Entity(Base):
    __tablename__ = 'pharmaceutical_entities'
    __table_args__ = (UniqueConstraint('owner_id', 'name', 'type'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    original_name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(50), index=True)
    synonyms: Mapped[list] = mapped_column(JSON, default=list)
    identifiers: Mapped[dict] = mapped_column(JSON, default=dict)

class Mention(Base):
    __tablename__ = 'entity_mentions'
    __table_args__ = (UniqueConstraint('entity_id', 'passage_id'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    entity_id: Mapped[str] = mapped_column(ForeignKey('pharmaceutical_entities.id', ondelete='CASCADE'), index=True)
    passage_id: Mapped[str] = mapped_column(ForeignKey('document_chunks.id', ondelete='CASCADE'), index=True)
    original: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(50), default='curated_dictionary')

class Relation(Base):
    __tablename__ = 'extracted_relationships'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    source: Mapped[str] = mapped_column(ForeignKey('pharmaceutical_entities.id', ondelete='CASCADE'), index=True)
    target: Mapped[str] = mapped_column(ForeignKey('pharmaceutical_entities.id', ondelete='CASCADE'), index=True)
    type: Mapped[str] = mapped_column(String(80))
    passage_id: Mapped[str] = mapped_column(ForeignKey('document_chunks.id', ondelete='CASCADE'), index=True)
    evidence: Mapped[str] = mapped_column(Text)
    negated: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(40), default='reported_finding')
    method: Mapped[str] = mapped_column(String(50), default='explicit_pattern_v1')

class ResearchSession(Base):
    __tablename__ = 'research_sessions'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(200), default='General research')
    created_at: Mapped[str] = mapped_column(String(40), default=now)

class Message(Base):
    __tablename__ = 'research_messages'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey('research_sessions.id', ondelete='CASCADE'), index=True)
    question: Mapped[str] = mapped_column(Text)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=now)

class Bookmark(Base):
    __tablename__ = 'bookmarks'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    passage_id: Mapped[str] = mapped_column(ForeignKey('document_chunks.id', ondelete='CASCADE'))
    note: Mapped[str] = mapped_column(Text, default='')

class Log(Base):
    __tablename__ = 'agent_execution_logs'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    agent: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[float]
    created_at: Mapped[str] = mapped_column(String(40), default=now)

class Audit(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    action: Mapped[str] = mapped_column(String(100))
    object_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[str] = mapped_column(String(40), default=now)

class IngestionJob(Base):
    __tablename__ = 'ingestion_jobs'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey('research_documents.id', ondelete='CASCADE'), index=True)
    status: Mapped[str] = mapped_column(String(20))
    stages: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
