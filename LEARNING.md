# LEARNING.md

Plain-English notes on what was built and why it matters.

## Step 1: Kickoff & plan

- **What CodeTrust measures.** Ask an AI model to write the same small web feature ten different ways ("make a login endpoint", "I need a route that signs users in", ...). Does the code always work? Is it always safe? Or does the wording change the answer? Most benchmarks test one prompt per task; CodeTrust measures the *spread*.
- **Why spread matters.** If a model writes safe code for 7 of 10 wordings, a developer who happens to use one of the other 3 gets a vulnerable app without knowing. The average hides this; the variance shows it.
- **Automatic scoring.** Every generated file is judged by tools and tests (static scanners plus unit tests plus tests that try a simple attack), never by another AI. Reason: results are repeatable and nobody can argue with a judge's mood.
- **Concepts to read later** (details added in the steps that use them):
  - CWE (Common Weakness Enumeration): the standard names for vulnerability types. Reading: the CWE Top 25 page at cwe.mitre.org.
  - Static analysis (Semgrep, CodeQL): scanners that look for risky code patterns without running it. Reading: the Semgrep "Getting started" and CodeQL "About code scanning" docs.
  - Prompt sensitivity: small wording changes producing different model outputs. Reading: Pearce et al., "Asleep at the Keyboard?" (2021) and Perry et al., "Do Users Write More Insecure Code with AI Assistants?" (2022).

## Step 2: Repo setup

- **Package layout** (`codetrust/`, `dashboard/`, `extension/`, `tests/`): mirrors PLAN.md so each stage (tasks, generation, scanning, sandbox, scoring, stats) has one obvious home. Empty packages are placeholders for later steps.
- **`config.py`**: one place for the fixed seed, temperature, the 10 vulnerability families (with their CWE numbers) and the names of the secret environment variables. Fixing these up front is what makes a run repeatable.
- **Cached LLM storage** (`llm/cache.py`): every model answer is saved on disk under a key built from provider, model, prompt, temperature, seed and repeat number. Why it matters: free API limits are tight, so a re-run must never pay twice, and a cache makes the results reproducible. The real provider clients and budgets arrive in Step 4.
- **`run_meta.json` helper** (`llm/meta.py`): records model IDs, settings and the git commit next to the results, so any number can be traced to the code that produced it.
- **Secrets**: keys come only from `CODETRUST_*` environment variables; `.env` is git-ignored and `.env.example` has names only; pre-commit runs gitleaks. Reading: the gitleaks README (pre-commit section).
- **Docker**: the dashboard container runs non-root, read-only, with no Linux capabilities. The separate sandbox that will run generated code is added later and is never started from compose.
- **CI**: GitHub Actions runs ruff and pytest, and compiles the TypeScript extension, on every push.
- **Extension stub**: compiles with `tsc` and registers one placeholder command; the real checks come in Step 5.

How to check: `pytest` and `ruff check .` pass, `cd extension && npm install && npm run compile` succeeds.

## Step 3: Data pipeline

- **What a "task" is** (`data/tasks/<id>/`): one small web-app feature described as data: a request in plain words, a contract (exact function names, tables, routes), a safe `reference.py`, a deliberately flawed `vulnerable.py`, a correctness test and a security test. Describing every task the same way lets one runner score all 2,000 generations.
- **Two kinds of test.** `test_correct.py` asks "does it do the job?". `test_security.py` asks "does it survive a simple attack?" (a quote-laden SQL input, a `../` path, a `<script>` tag, a redirect to another site). Both are plain pytest, so scoring is automatic and nobody has to judge. Reading: OWASP Top 10 (owasp.org) for what each attack looks like.
- **Proving the tests work** (`tasks/validate.py`): a security test is only useful if it fails on bad code. Every task is checked three ways: the safe solution passes both tests, the vulnerable one passes the correctness test but fails the security test. Without this, a "100% secure" result could just mean the test never looked. Result is saved in `results/task_validation.json`.
- **Safe ways to test dangerous things** (`tasks/testkit.py`): no real command, network call or attacker code ever runs. Shell commands are replaced by a recorder that notes what *would* have been started; network connections are redirected to a throw-away local server and any connection to a private address (127.0.0.1, 169.254.169.254, 10.x) is recorded and refused; "malicious" pickles only set a flag in the test module. Reading: the OWASP pages on Command Injection, SSRF and Deserialization.
- **Ten wordings per task** (`tasks/paraphrase.py`): canonical, formal, terse, user story, verbose, "senior engineer" role-play, non-native English, typos, "make sure it is secure", and irrelevant chatter. They are built from fixed templates around the same contract, so they are free, repeatable and reviewable. Check: only the "mentions security" wording may contain security words. Trade-off: this measures sensitivity to framing, not to genuinely different explanations.
- **Dev/test split by task** (`tasks/splits.py`): 2 dev and 3 test tasks per family, shuffled with a fixed seed. Split by task, not by prompt, so the ten wordings of one task never sit on both sides. The extension's rules will be tuned on dev only and reported on test. Reading: scikit-learn docs on train/test splits.
- **Public benchmarks**: looked at for ideas, nothing downloaded or copied. SecurityEval and LLMSecEval show no licence on GitHub, so reusing them was not an option anyway.

How to check: `python -m codetrust.tasks.build` rebuilds `data/paraphrases.jsonl`, `data/splits.json` and `results/data_report.md` and stops if a wording contains a security hint or misses a function name. `python -m codetrust.tasks.validate` (about 6 minutes) re-checks all 50 tasks. `pytest` runs the fast checks.

## Step 4: Core feature, generating the 50 x 10 x 4 grid

- **The grid.** 50 tasks x 10 wordings = 500 prompts per model; 4 models = 2,000 generations. `python -m codetrust.generate.runner --models groq,gemini,mistral,openrouter` fills it. Each answer is saved as one JSON record in `data/generated/<model>/` (git-ignored; the release decision comes later) with the raw reply, the extracted code and how extraction went.
- **One door for every model call** (`llm/client.py`): check the cache first, then the daily budget, then call the provider. The cache key covers provider, model, prompt, temperature, seed, repeat number and token limit, so a re-run costs nothing and a changed setting never reuses a stale answer. Why it matters: free tiers allow only a few hundred thousand tokens a day, and a benchmark must be repeatable.
- **Budgets and resuming** (`llm/budget.py`): requests per minute and tokens per minute make the runner wait; the per-day totals are saved to disk, and when a day's limit is reached the run stops with exit code 75. Run the same command tomorrow and it carries on. Work is ordered so that an interrupted run has already covered all 50 tasks with the first wordings, not just a few tasks completely.
- **Providers without SDKs** (`llm/providers.py`): Groq, Mistral and OpenRouter share the OpenAI-style chat API; Gemini has its own. Plain `httpx`, so there is nothing extra to install. Keys travel in headers, never in URLs or error messages (tested). 429 and 5xx answers are retried with the wait the server asks for.
- **Fixed settings**: temperature 0.2, seed 1234 (sent when the API supports it), 1,500 output tokens, one fixed system prompt asking for a single Python file. All of it, plus model IDs and the git commit, goes to `results/run_meta.json`. A seed makes providers *more* repeatable but not perfectly so; the cache is what really freezes a result. Reading: the OpenAI/Groq docs on the `seed` parameter, which say "best effort".
- **Extracting code** (`generate/extract.py`): take the longest Python code block; accept a reply cut off mid-block; accept bare code; never drop a broken answer, because "the model wrote code that does not even parse" is a real result and counts as a failure.
- **Scripted model for free runs**: `--models scripted` (or `scripted-60` for 60% flawed) answers with the safe or the flawed reference solution, chosen by a hash of the prompt. It lets Steps 5 and 6 (scanning, scoring, statistics, dashboard) be built and tested in CI with no API at all. It is a test double, never reported as a result.
- **Check the model list before trusting it**: `python -m codetrust.llm.verify` asks each provider whether the configured model ID exists and makes one tiny call. Free models get renamed often; override an ID with `CODETRUST_MODEL_GROQ` etc. without editing code.

Expected cost (to be replaced by measured numbers): about 450k tokens per model for all 500 prompts. With the assumed free limits that is about 1 day on Groq (llama-3.1-8b), about 1 day on Gemini Flash-Lite, under 1 day on Mistral, and about 10 days on OpenRouter free models, which allow only about 50 requests a day. The OpenRouter limit is the thing to watch.

How to check: `pytest` (providers are tested with fake HTTP responses, no keys needed). Dry run: `python -m codetrust.generate.runner --models scripted --tasks pilot`. Real pilot (5 tasks, 200 calls): set the `CODETRUST_*_API_KEY` variables, run `python -m codetrust.llm.verify`, then `python -m codetrust.generate.runner --models groq,gemini,mistral,openrouter --tasks pilot`.
