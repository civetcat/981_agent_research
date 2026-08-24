# AGENTS.md

## Cursor Cloud specific instructions

### What is runnable here
This repo is mostly Cursor Skills / prompt / rules documentation. The **only runnable
application** is the **Stock Simulator** under `todo/daniel/` (台股/美股 模擬・回測・選股・AI 分析):

- **Backend**: `todo/daniel/backend` — Python + FastAPI + SQLAlchemy + SQLite.
- **Frontend**: `todo/daniel/frontend` — React + TypeScript + Vite + Tailwind.

Standard commands and full feature docs live in `todo/daniel/README.md`. The `scripts/*.ps1`
/ `*.cmd` launchers in that folder are **Windows-only**; on Linux start the two dev servers
manually (see below).

### Startup (dev)
The update script already installs deps (backend `.venv`, frontend `node_modules`) and creates
`todo/daniel/backend/.env` from `.env.example`. To run the app:

- Backend (run **from `todo/daniel/backend`** — this is required):
  `\.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend (from `todo/daniel/frontend`): `npm run dev` (serves on `:5173`).

### Non-obvious caveats
- **CWD matters for the backend.** `config.py` loads `.env` and the SQLite DB
  (`sqlite:///./stocksim.db`) as paths *relative to the current working directory*. Always
  launch uvicorn from `todo/daniel/backend/`, or the `.env` and DB won't be found/created where
  expected.
- **Backend must be on port 8000.** Vite proxies `/api` → `http://localhost:8000` (see
  `frontend/vite.config.ts`), so the frontend only works when the backend is up on 8000.
- **Runs with zero secrets in `single` mode (the default).** `GROK_API_KEY` (xAI) and
  `FINMIND_TOKEN` are optional; without them AI features fall back to rule-based Chinese
  summaries and TW fundamentals fall back to yfinance. No login/account is required.
- **Network egress is required for market data.** yfinance / TWSE / TPEX / Nasdaq / FinMind are
  called at runtime. App startup runs `listings.enrich_names`, which hits external APIs but is
  wrapped and non-fatal, so the server still starts if a source is unreachable.
- **Python version.** README recommends 3.13; the VM has 3.12, which works fine for the pinned
  numpy/pandas. Creating the venv needs the `python3.12-venv` system package.
- **Generated/ignored artifacts.** `backend/.venv`, `backend/stocksim.db`, `backend/data_cache/`,
  and `frontend/node_modules` are gitignored — do not commit them.

### Verify / lint / build
- Backend import check: from `todo/daniel/backend`, `\.venv/bin/python -c "from app.main import app; print(app.title)"`.
- Frontend type check: from `todo/daniel/frontend`, `npx tsc --noEmit`.
- Frontend build: from `todo/daniel/frontend`, `npm run build`.
- There is no dedicated backend test suite or Python linter configured; smoke-test via
  `curl http://127.0.0.1:8000/api/health` and the endpoints listed in `todo/daniel/README.md`.
