# Verification record

Executed locally on Windows using the bundled Python 3.12.14 and Node 24.22.1. The system's Python 3.15 was intentionally not used. Tests operate on isolated temporary data and fictional documents, without external credentials.

Verified before handoff:

- Backend integration suite: **21 passed, zero failures/skips**, final complete run in 60.45 seconds. Coverage includes real multi-page PDF and DOCX extraction, embedded PDF authors, all accepted formats, failures, duplicates, owner isolation, role restrictions, entities/aliases/corrections, negated graph evidence/paths, retrieval modes/filters, citation validation, unrelated-question abstention, sessions/bookmarks, comparisons/conflicts, provider fabrication rejection, mocked official API connectors, and real FAISS index persistence/score parity.
- Frontend suite: 10 tests passed, including authentication, file upload, repository search, research chat, page citations, entity categories, graph rendering/expansion controls, evidence search, comparison, and visible request errors. API responses are mocked. This does not replace full browser end-to-end testing.
- TypeScript `tsc -b`: passed.
- Vite production build: passed. It emits a warning about a JavaScript chunk above 500 kB; code splitting is a performance follow-up.
- Frontend production dependency audit after upgrades: zero reported known vulnerabilities.
- Installed backend dependency audit after upgrades: zero reported known vulnerabilities. `pip check`: no broken requirements.
- CLI initialization: database schema initialized.
- Alembic: upgrade completed; `current` returned `0001 (head)`.
- Local production preview root and `/app/graph`: HTTP 200. Preview `/api/v1/health` successfully proxied to this project's backend and returned status `ok`.

Remaining verification limits:

- The in-app browser repeatedly timed out and subsequently showed a connection-reset error. Visual layout, mobile interaction, real graph dragging/edge clicks and full browser journeys were not verified. HTTP checks and component tests passed independently.
- Docker was not available in the command environment. Docker/Compose configuration and non-root volume behavior need execution on a Docker-capable host.
- PostgreSQL, a running Neo4j service, pretrained SentenceTransformer downloads and a paid provider API were not exercised. The provider's invalid-output fallback was tested with a mock.
- Official source connector tests mock responses. Live source availability, changing terms/rate limits, and rights to any imported content require separate verification.
- At the initial handoff no cloud deployment had been performed. A subsequent user-authorized frontend-only Vercel deployment is now live and HTTP-verified; see `deployment.md`. The backend remains local. No biomedical extraction, retrieval quality, clinical accuracy or safety benchmark is claimed.

Optional FAISS: version 1.11.0 was installed and exercised. The test verified a persisted `.faiss` file, a JSON passage-ID mapping, equivalent ranked scores to the SQL vector path, and stable results on cache reload. Its package was included in the zero-vulnerability installed-environment audit. The final test run has five upstream PyMuPDF/SWIG deprecation warnings; they do not indicate extraction failures. An earlier FAISS test setup was blocked by the shared system pytest temp directory; the fixture now creates isolated per-run temporary directories and the final full suite passes.

## Backend deployment preparation follow-up

After the user's detailed Render deployment request, the existing project and remote hosting state were inspected again. Render login and the selected workspace were verified; the workspace had no services. No Git remote exists, and the user requested guidance to create/connect a private repository without granting GitHub account access or source-push authorization.

Production CORS now uses only the exact configured HTTPS origin; free Render startup rejects local SQLite or filesystem upload storage. Health checks query the database and return 503 if unavailable. The frontend accepts `VITE_API_BASE_URL` and retains the existing `VITE_API_URL` fallback. No live Vercel environment was changed.

Latest local verification: **27 backend tests passed** (57.99 seconds), **10 frontend tests passed**, TypeScript and production build passed. Render Blueprint validation returned `valid: true`, proposing one Free web service and one Free PostgreSQL database. Validation created no resources. The backend still has no deployed URL, and hosted frontend-to-backend communication cannot be tested until the repository/source and deployment exist. See `render-deployment-runbook.md` for the exact next steps and free-tier retention limits.
