# Architecture

React is a REST client; SQL is the authoritative evidence store. `backend/app/main.py` defines protected routes. `ingestion.py` extracts and chunks files; `nlp.py` identifies supported terms and explicit relations; `vectors.py` creates persisted representations; `graph.py` builds an owner-scoped NetworkX multigraph and optionally mirrors it to Neo4j; `retrieval.py` ranks passages; `research.py` coordinates a typed LangGraph pipeline and validates source excerpts.

An ingestion job is committed before extraction. Success atomically replaces chunks, mentions, relations and document status; failure rolls back that work and persists a failed state with an actionable extraction error. Upload bytes use a random document ID, and are never served as executable HTML. Deleting a document cascades through its evidence records.

Every private request resolves a JWT to a stored user. Owner checks occur before loading documents, sessions, entities, bookmarks and relation evidence. External services are optional. Startup is network independent in default configuration. State persists under `runtime/`; back it up with a consistent database snapshot and uploaded files. Scale-out requires shared storage and a task queue.
