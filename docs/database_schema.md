# Database schema

| Table | Purpose and ownership |
| --- | --- |
| users | Unique normalized email, password hash, name, role |
| research_documents | Owner FK, unique owner/hash, file name/type, status/error, JSON metadata/references, timestamp |
| document_chunks | Document FK, exact passage, page, section, ordinal, vector JSON |
| pharmaceutical_entities | Owner FK, unique owner/name/type, original and normalized names, synonyms/identifiers JSON |
| entity_mentions | Entity and passage FKs, surface text, extraction method |
| extracted_relationships | Entity endpoints, type, passage FK, exact evidence, negation, status/method |
| ingestion_jobs | Document FK, pipeline stages and status |
| research_sessions | Owner FK, title/topic, timestamp |
| research_messages | Session FK, question, full response/evidence JSON, timestamp |
| bookmarks | Owner FK, passage FK, note |
| agent_execution_logs | Owner/run IDs, stage, duration, details, timestamp |
| audit_logs | Owner/action/object/time |

Chunk, mention, relationship, bookmark, message and ingestion-job foreign keys cascade on their respective parent deletion. Owner IDs, entity names/types, passage/document joins and run IDs have indexes. Metadata, references, identifiers, synonyms, vector payloads and generated evidence packages are deliberately embedded in their owning records. Historical response JSON can contain an old passage snapshot after a document is deleted; re-run retrieval to validate current evidence.

SQLite enables foreign keys on each connection. PostgreSQL uses SQLAlchemy's psycopg dialect. Alembic contains the initial schema revision. Before evolving models, create and review a migration; model startup does not alter existing tables.
