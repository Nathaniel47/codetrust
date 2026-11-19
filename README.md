# CodeTrust: Security of AI-Generated Code

A benchmark plus VS Code extension that measures how secure and correct LLM-generated web-app code is, and how much that changes when the same request is worded differently.

**Status:** setup stage (Step 2 of 8). See [PLAN.md](PLAN.md) for the design and [BUILD_STEPS.md](BUILD_STEPS.md) for progress. Demo link, results and architecture diagram are added in Step 8.

## Run locally

Requires Python 3.11, Docker (for scanners and the code sandbox, later steps) and Node 20 (extension only).

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env   # then fill in keys; never commit .env
pytest
ruff check .
streamlit run dashboard/app.py
```

**macOS / Linux**

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env     # then fill in keys; never commit .env
pytest && ruff check .
streamlit run dashboard/app.py
```

**Docker** (dashboard only): `docker compose up --build`, then open http://localhost:8501.

**Extension**: `cd extension && npm install && npm run compile`.

## Secrets

Keys are read only from environment variables named `CODETRUST_*` (see `.env.example`). Enable the hooks with `pre-commit install` (includes a gitleaks scan).

## Safety

Generated code is only analysed or run inside a locked-down sandbox, never against real services or data. All test data is synthetic.

## Licences and data sources

Recorded in Step 3 (tasks are self-written; public benchmarks are used for reference only).
