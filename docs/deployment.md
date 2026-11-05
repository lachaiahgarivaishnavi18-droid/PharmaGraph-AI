# Vercel frontend deployment

Production URL: https://pharmagraph-ai-nine.vercel.app

Deployed to the authenticated Vercel account as a new `pharmagraph-ai` project, following the user's explicit choice to deploy the frontend first.

- Vercel deployment: `dpl_FG4j6DPzSpbrYVmuoPT389eGNXBX`.
- Production state returned by Vercel: `READY`.
- Production root and `/app/assistant` verified over HTTPS: HTTP 200.
- Deployed JavaScript verified to contain the backend-hosting-pending notice.
- The backend, database and document storage are not deployed. Sign-in, uploads and research are intentionally unavailable on the hosted frontend until API hosting is connected.

The production build uses `VITE_BACKEND_PENDING=true` so the hosted interface states this limitation and avoids making broken API requests. To connect a future backend, set `VITE_API_URL=https://YOUR_BACKEND/api/v1`, remove or set `VITE_BACKEND_PENDING=false`, configure the backend's `FRONTEND_URL=https://pharmagraph-ai-nine.vercel.app`, and redeploy.

The local production build was restored without the pending flag so it can continue using the existing localhost API proxy. Vercel project linkage is kept in ignored `frontend/.vercel/`; no account credential was added to the repository.

## Free-only backend preparation

The user subsequently required free hosting only. Railway refused creation due to its free-plan resource limit. Render CLI login was completed and the selected workspace is `My Workspace`; no services existed when checked.

`render.yaml` now explicitly selects only `plan: free` for a Docker web service and PostgreSQL, with no paid persistent disk. Render validation returned `valid: true` and a proposed two-resource plan. Validation did not create or deploy resources.

Original document bytes can now persist in the `document_files` SQL table with `DOCUMENT_STORAGE=database`, instead of the free web server's ephemeral filesystem. The `0002` migration adds this table. This mode supports reprocessing after web-server restarts and cascades stored bytes on document deletion.

Important: [Render Free PostgreSQL expires after 30 days](https://render.com/docs/free), has 1 GB of capacity, and does not include backups. The free API sleeps when idle. This is a temporary demo configuration; no paid upgrade or resource is authorized.

Backend publication remains pending a hosted source repository or published image. There is no Git remote configured. Creating a private GitHub repository and using GitHub authentication still requires the user's explicit source choice; a prior credential check was rejected by automatic approval review before execution.
