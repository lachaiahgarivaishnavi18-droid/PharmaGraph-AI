# Verified live deployment

Frontend: https://pharmagraph-ai-nine.vercel.app
Backend: https://pharmagraph-api.onrender.com
Health: https://pharmagraph-api.onrender.com/api/v1/health
Repository: https://github.com/lachaiahgarivaishnavi18-droid/PharmaGraph-AI (main)

## Render

- Existing workspace: My Workspace.
- Web service: pharmagraph-api, srv-dbmc122jnfac73915ts0.
- Runtime: Docker (Python 3.12), region Singapore, compute plan free, one instance.
- Database: pharmagraph-demo-db, dpg-dbmc1sg8v5cc73e5vhj0-a, PostgreSQL 17, plan free.
- Application deployment dep-dbmc38h42hec73e8h30g reached live on source commit f12dc960eecc968d2f9a2f981a1a6db58dbb07c4.
- Public health verified HTTP 200 with status=ok and database=ok.
- No paid persistent disk, database plan, or compute plan was selected.

Database credentials and a generated JWT secret were configured only in Render environment variables. They were not printed or written into repository files. Original uploads use database storage; local filesystem persistence is not assumed.

The initial service deployment failed closed because the database variable was not configured yet. After the free database became available and production variables were configured, the next deployment passed. The free database rejects explicit disk-size changes; it was created using its fixed default capacity without selecting a paid plan.

## Existing Vercel project

- Existing project: pharmagraph-ai. Its original production alias was preserved.
- Production deployment dpl_Fq6QsnbmWHuD5B6eur5MNo9qghCz returned READY.
- VITE_API_BASE_URL=https://pharmagraph-api.onrender.com/api/v1
- VITE_BACKEND_PENDING=false
- The deployed JavaScript bundle was verified to contain the Render API base URL and no longer include the frontend-only notice.
- The open frontend tab was refreshed and the old pending notice was confirmed absent.

## Live verification

Public health, exact-origin CORS preflight, rejection of an unrelated origin, anonymous API protection, registration/login/me, real PDF upload, page metadata, graph extraction, hybrid retrieval, cited answers, session history, validation errors, and SQL-backed original-document reprocessing all passed. Tests used a separate synthetic verification account and fictional document; no existing user data was changed. Live PostgreSQL was exercised through these APIs, not by running the destructive test fixture against production.

Local checks: 27 backend tests passed; 10 frontend tests passed; TypeScript, frontend build, package consistency and Render Blueprint validation passed. The Docker image built successfully on Render.

## Limits

The free database expires on 5 December 2026 (provider timestamp: 2026-12-05T17:46:26.85057Z). Capacity is 1 GB and managed backups are not included. The free web service sleeps when idle. Included bandwidth/build quotas apply. This is a verified demo deployment, not permanent production infrastructure. No paid upgrade is authorized.

Use the existing services when making changes. Do not create a duplicate Vercel project, Render service or database. Backend automatic rebuilds are filtered to backend/**, scripts/**, data/**, Dockerfile, .dockerignore and render.yaml so documentation/frontend-only commits do not consume backend build minutes.

See render-production-settings.md for exact settings and the Vercel connection steps.
