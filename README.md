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

## Generate code with the models

```bash
python -m codetrust.llm.verify                                   # check model IDs and keys
python -m codetrust.generate.runner --models groq --tasks pilot  # 5 tasks x 10 wordings
python -m codetrust.generate.runner --models groq,gemini,mistral,openrouter
python -m codetrust.generate.runner --models scripted            # free offline test model
```

A run that hits a daily free-tier limit exits with code 75; run the same command again after 00:00 UTC. Answers are cached, so nothing is paid for twice.

## Secrets

Keys are read only from environment variables named `CODETRUST_*` (see `.env.example`). Enable the hooks with `pre-commit install` (includes a gitleaks scan).

## Safety

Generated code is only analysed or run inside a locked-down sandbox, never against real services or data. All test data is synthetic.

## Dataset

- `data/tasks/<id>/`: 50 self-written tasks (5 for each of 10 vulnerability families). Each has `task.json` (request and contract), `reference.py` (safe solution), `vulnerable.py` (deliberately flawed solution), `test_correct.py` and `test_security.py`.
- `data/paraphrases.jsonl`: 500 prompts (10 wordings per task). `data/splits.json`: seeded dev/test split by task (20 dev, 30 test).
- `results/data_report.md`: counts, sample records and quality problems. `results/task_validation.json`: proof that each security test fails on the vulnerable solution and passes on the reference.
- Rebuild: `python -m codetrust.tasks.build`. Check every task (several minutes): `python -m codetrust.tasks.validate`.

## Licences and data sources

Checked 2026-11-20.

| Source | How it is used | Licence / terms |
|---|---|---|
| Tasks, paraphrases, tests (this repo) | Written for this project, no text copied from elsewhere | Code MIT; dataset CC BY 4.0 (proposed, to be confirmed before release) |
| HumanEval (openai/human-eval) | Reference only, nothing copied | MIT |
| SecurityEval (s2e-lab/SecurityEval) | Reference only, nothing copied | No licence declared on GitHub, so no content reused |
| LLMSecEval (tuhh-softsec/LLMSecEval) | Reference only, nothing copied | No licence declared on GitHub, so no content reused |
| CyberSecEval (meta-llama/PurpleLlama) | Reference only, nothing copied | Mixed licences across the repo, not used |
| Test dependencies: Flask, requests, PyYAML, cryptography | Imported by tests and by reference solutions | BSD-3 / Apache-2.0 / MIT / Apache-2.0 or BSD |

Still to check before use: Semgrep rule licence and CodeQL terms (Step 5), and each model provider's terms on publishing generated code (Step 4).

All test data is synthetic: users, emails and secrets are made up and use `.test` / `example.test` domains.
