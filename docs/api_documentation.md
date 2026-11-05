# API

Base: `/api/v1`. OpenAPI: `/openapi.json`; interactive docs: `/docs`. Register and login accept JSON; other private routes use bearer JWT. Pydantic rejects invalid lengths, weights, ranges, graph hops and top-k. Missing private records return 404 to avoid disclosure; duplicates by file return the existing record with `duplicate: true`; unsupported files return 415; processing errors are persisted as failed documents.

- `POST /auth/register`, `/auth/login`; `GET /auth/me`, `/health`.
- `GET /documents` with q/offset/limit/year/document_type; `POST /documents/upload` multipart `files` (up to five); `GET /documents/export`; `GET/DELETE /documents/{id}`; `POST /documents/{id}/process`; `GET /documents/{id}/chunks`.
- `GET /entities` with q/type/offset/limit; `POST /entities/extract`, `/entities/normalize`; `GET/PATCH /entities/{id}`; `GET /entities/{id}/relationships`.
- `GET /graph`, `/graph/stats`, `/graph/entity/{id}`, `/graph/related/{id}`, `/graph/paths`, `/graph/evidence/{id}`; `POST /graph/build`.
- `POST /retrieval/{semantic|keyword|hybrid|graph}`.
- `POST /research/ask`, `/research/summarize`, `/research/compare`, `/research/conflicts`, `/research/evidence-check`.
- `GET/POST /research/sessions`; `GET /research/sessions/{id}`; `GET/POST /research/bookmarks`; `DELETE /research/bookmarks/{id}`.
- `GET /analytics/{dashboard|documents|entities|graph|retrieval}`; `GET /agents/logs`; `POST /demo/seed`.
- `GET /sources/pubmed/search`, `/sources/europe-pmc/search`, `/sources/clinical-trials/search`, `/sources/uniprot/search` with q; `GET /sources/pubchem/compound/{numeric-cid}`.

Example search request:

```json
{"query":"Drug Aster Target Sigma","top_k":8,"min_score":0.03,"year_from":2023,"year_to":2025,"graph_hops":1,"document_ids":[],"entity_ids":[],"weights":{"vector":0.4,"keyword":0.25,"graph":0.25,"metadata":0.1}}
```

Ask accepts the same controls plus an optional session_id. Comparison accepts `left` and `right` text topics. Evidence-check accepts `{query: <Search>, response: <previous answer>}` and revalidates against freshly retrieved passages. Source discovery is read-only; no user URL is fetched and no paywall is bypassed.
