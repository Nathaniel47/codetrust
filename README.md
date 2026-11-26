# CodeTrust: Security of AI-Generated Code

A benchmark plus VS Code extension that measures how secure and correct LLM-generated web-app code is, and how much that changes when the same request is worded differently.

**Status:** features and evaluation code built (Step 6 of 8 in progress). A 50-request pilot on `openai/gpt-oss-20b` has run; the full experiments have not, so there are no results to report yet. See [PLAN.md](PLAN.md) for the design and [BUILD_STEPS.md](BUILD_STEPS.md) for progress. Demo link, results and architecture diagram are added in Step 8.

## Run locally

Requires Python 3.11, Docker (for scanners and the code sandbox, later steps) and Node 20 (extension only).

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
ruff check .
streamlit run dashboard/app.py
```

**macOS / Linux**

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest && ruff check .
streamlit run dashboard/app.py
```

**Docker** (dashboard only): `docker compose up --build`, then open http://localhost:8501.

**Extension**: `cd extension && npm install && npm run compile`.

## Generate code with the models

```bash
python -m codetrust.llm.verify                                   # check model IDs and keys
python -m codetrust.generate.runner --models groq --tasks pilot  # 5 tasks x 10 wordings
python -m codetrust.generate.runner --models groq,gemini
python -m codetrust.generate.runner --models scripted            # free offline test model
```

A run that hits a daily free-tier limit exits with code 75; run the same command again after 00:00 UTC. Answers are cached, so nothing is paid for twice.

## Score the generations

Needs Docker (images: `codetrust-sandbox`, `semgrep/semgrep`).

```bash
docker build -t codetrust-sandbox -f docker/Dockerfile.sandbox .
docker pull semgrep/semgrep:latest
python -m codetrust.scan.validate               # how good is the scanner on known answers?
python -m codetrust.score.run --models scripted-60
streamlit run dashboard/app.py                  # per model, per family, wording effect, drill-down
```

Generated code only ever runs inside the sandbox container (no network, read-only, non-root).

## Evaluate

```bash
python -m codetrust.generate.runner --models groq,gemini --tasks noise --repeats 3   # noise
python -m codetrust.generate.runner --models groq,gemini --reminder                  # baseline
python -m codetrust.score.run --models groq,gemini,groq+reminder,gemini+reminder
python -m codetrust.evaluate.report                                                  # tables, charts, limitations
```

Run these after the main generation. Output goes to `results/evaluation/`. With only the offline test model it goes to `results/evaluation_dryrun/` and is stamped DRY RUN.

## VS Code extension

```bash
cd extension && npm install && npm test         # rule tests
npm run evaluate                                # precision/recall on dev and held-out test tasks
npx @vscode/vsce package --no-dependencies      # builds the .vsix
```

## Secrets

Keys are read only from environment variables named `CODETRUST_*` (names are listed in `.env.example`). Set them in your shell or as user environment variables: the Python commands do not load a `.env` file (only `docker compose` does). Enable the hooks with `pre-commit install` (includes a gitleaks scan).

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
| Tasks, paraphrases, tests (this repo) | Written for this project, no text copied from elsewhere | Code: MIT ([LICENSE](LICENSE)). Dataset (`data/tasks/`, `data/paraphrases.jsonl`, `data/splits.json`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), credit Nathaniel Ankomah Aidoo |
| HumanEval (openai/human-eval) | Reference only, nothing copied | MIT |
| SecurityEval (s2e-lab/SecurityEval) | Reference only, nothing copied | No licence declared on GitHub, so no content reused |
| LLMSecEval (tuhh-softsec/LLMSecEval) | Reference only, nothing copied | No licence declared on GitHub, so no content reused |
| CyberSecEval (meta-llama/PurpleLlama) | Reference only, nothing copied | Mixed licences across the repo, not used |
| Test dependencies: Flask, requests, PyYAML, cryptography | Imported by tests and by reference solutions | BSD-3 / Apache-2.0 / MIT / Apache-2.0 or BSD |

### Scanner and model providers (terms read 2026-11-25)

| Service | Status | Why |
|---|---|---|
| Semgrep | Used | The rules in `data/rules/` are our own; no registry rules are used or shipped |
| [Groq](https://console.groq.com/docs/legal/services-agreement) (last modified 2026-06-22) | Used | Customer keeps the rights in output (8.1). No publicity or pre-approval clause found for publishing output. Generated code may carry third-party licences (4.3). The use policy and this model's licence were read on 2026-11-26 (next row) |
| [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b/blob/main/LICENSE) on Groq (read 2026-11-26) | **The benchmark model** | Weights are Apache-2.0; OpenAI's usage policy asks only for compliance with the law; Groq's [use policy](https://console.groq.com/docs/legal/ai-policy) (effective 2025-10-15) has no approval step for ordinary code generation and forbids going past rate limits, for example with extra accounts |
| [Gemini API](https://ai.google.dev/gemini-api/terms) (effective 2026-03-23) | Supported, not used (no key) | Google does not claim the output. No pre-approval clause found. On the unpaid tier Google uses prompts and output to improve its products and people may review them (our prompts are synthetic). **Not read:** the general Google APIs terms and use policy |
| [Mistral](https://legal.mistral.ai/terms/commercial-terms-of-service) (effective 2026-09-25) | Removed | Using its name publicly needs written approval (14.4) and "performance information" is confidential (6.1). These are the business terms; the consumer terms were not read |
| [OpenRouter](https://openrouter.ai/terms) (updated 2026-08-31) | Removed | Rights in output depend on separate per-model terms (6.1) that were not read. Its red-teaming approval rule (7, 8) does not appear to cover ordinary coding requests. About 50 free requests a day was also too slow |
| [CodeQL](https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md) | Removed | Allowed only for academic research or open-source codebases; neither clearly covers real model output. Earlier CodeQL results remain in git history |

This is a project record, not legal advice.

All test data is synthetic: users, emails and secrets are made up and use `.test` / `example.test` domains.
