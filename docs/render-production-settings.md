# Exact Render settings and Vercel connection

The backend is deployed and its public database-aware health endpoint is verified. Use the existing resources below rather than creating duplicates.

| Setting | Value |
| --- | --- |
| Existing Render service | `pharmagraph-api` |
| Dashboard | https://dashboard.render.com/web/srv-dbmc122jnfac73915ts0 |
| Repository | https://github.com/lachaiahgarivaishnavi18-droid/PharmaGraph-AI |
| Branch | `main` |
| Root Directory | Leave blank: repository root |
| Environment / Runtime | **Docker**; Python 3.12 is selected by the existing Dockerfile |
| Dockerfile Path | `./Dockerfile` |
| Docker Context | `.` |
| Build Command | Leave blank. Render builds the Dockerfile, which runs `pip install --no-cache-dir -r backend/requirements.lock` |
| Start Command / Docker Command | Leave blank to use Docker CMD: `python /app/scripts/container_start.py` |
| Effective API command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health Check Path | `/api/v1/health` |
| Compute Plan | `free` |
| Region | Singapore |
| Instances | 1 |
| Backend URL | https://pharmagraph-api.onrender.com |
| Health URL | https://pharmagraph-api.onrender.com/api/v1/health |

The backend is FastAPI with SQLAlchemy/Pydantic, not a Node server. Its dependencies are in `backend/requirements.txt` and the resolved `backend/requirements.lock`. Node/pnpm are needed only to build the separate frontend. The Docker image sets `PYTHONPATH=/app/backend`, so the ASGI import is `app.main:app`, not `main:app` from the repository root.

## Required backend environment

| Name | Configuration |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DEPLOYMENT_TARGET` | `render-free` |
| `JWT_SECRET` | Strong generated secret already stored on Render. Preserve it; never put it in Git or Vite variables |
| `DATABASE_URL` | Existing database's **internal** connection string, stored only on Render; never print the value |
| `DOCUMENT_STORAGE` | `database` |
| `FRONTEND_URL` | `https://pharmagraph-ai-nine.vercel.app` |
| `STORAGE_PATH` | `/app/runtime`, temporary working files only |
| `VECTOR_STORE` | `sqlite`, the existing SQL vector-scan adapter; the actual production database is PostgreSQL |
| `EMBEDDING_MODEL` | `local-hashing-v1` |
| `LLM_PROVIDER` | `offline` |
| `MODEL_DOWNLOADS` | `false` |
| `PORT` | Supplied by Render; do not hardcode it |

Optional existing configuration: `MAX_UPLOAD_MB` defaults to 20, `RATE_LIMIT_PER_MINUTE` to 180. LLM API keys, Neo4j credentials and downloaded embedding models are not needed for the verified baseline. `.env.example` documents optional integrations without secrets.

The existing `render.yaml` defines a Free Docker service and Free PostgreSQL with a generated JWT secret and database reference. The live services were created through the CLI/API. Reuse them; do not create a second deployment from the Blueprint without checking resource ownership and names.

## Persistence and production limits

Users, metadata, passages, vectors, graph evidence, sessions and original upload bytes persist in PostgreSQL. `document_files.content` stores original uploads, so reprocessing does not depend on the web service's ephemeral filesystem. No paid persistent disk is used. CORS allows only the configured exact HTTPS frontend origin in production.

The existing Free PostgreSQL expires on **5 December 2026**, has **1 GB** capacity and no managed backups. The Free API sleeps on inactivity. Included usage quotas apply. This configuration is suitable for a demo, not permanent production storage. A paid upgrade requires separate user approval; an externally supplied durable database is another option. No paid resources were selected.

## Connect or reconnect the existing Vercel frontend

These steps have already been completed for the live deployment:

1. Verify the Render health URL returns HTTP 200 with `status: ok` and `database: ok`.
2. In the **existing** Vercel project `pharmagraph-ai`, open Settings → Environment Variables → Production.
3. Set `VITE_API_BASE_URL=https://pharmagraph-api.onrender.com/api/v1`.
4. Set `VITE_BACKEND_PENDING=false`.
5. Keep `FRONTEND_URL=https://pharmagraph-ai-nine.vercel.app` on Render.
6. Redeploy the existing Vercel project. Vite embeds configuration during the build; changing variables alone does not update an existing bundle.
7. Refresh https://pharmagraph-ai-nine.vercel.app. Its URL remains unchanged. The old backend-pending notice should be absent.
8. Check browser requests target the Render `/api/v1` URL. CORS preflight must return the exact frontend origin, and anonymous private routes must remain protected.

`VITE_API_URL` remains a backwards-compatible alias; `VITE_API_BASE_URL` takes precedence. Never expose database credentials, JWT secrets or LLM API keys through any `VITE_` variable.

## Verification performed

- Public health: HTTP 200, database connected.
- CORS: existing Vercel origin allowed; unrelated origin rejected.
- Live registration/login/me, real PDF upload/pages, graph extraction, hybrid retrieval, cited answers/history and SQL-backed reprocessing passed using isolated synthetic test data.
- Invalid file type returned 415; invalid retrieval input returned 422; private routes rejected anonymous access.
- Vercel deployed bundle contains the correct backend URL and no pending-only notice; frontend root and assistant SPA route returned 200.
- Local suite: 27 backend tests and 10 frontend tests passed; TypeScript, build, dependency consistency and Blueprint validation passed.

No application feature rewrite was necessary. The first incomplete-configuration deploy failed closed; configuring the database and secrets resolved it. Full browser chat interaction, load testing, recovery testing and clinical validation were not performed.
