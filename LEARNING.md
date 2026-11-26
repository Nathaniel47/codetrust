# LEARNING.md

Plain-English notes on what was built and why it matters.

## Step 1: Kickoff & plan

- **What CodeTrust measures.** Ask an AI model to write the same small web feature ten different ways ("make a login endpoint", "I need a route that signs users in", ...). Does the code always work? Is it always safe? Or does the wording change the answer? Most benchmarks test one prompt per task; CodeTrust measures the *spread*.
- **Why spread matters.** If a model writes safe code for 7 of 10 wordings, a developer who happens to use one of the other 3 gets a vulnerable app without knowing. The average hides this; the variance shows it.
- **Automatic scoring.** Every generated file is judged by tools and tests (static scanners plus unit tests plus tests that try a simple attack), never by another AI. Reason: results are repeatable and nobody can argue with a judge's mood.
- **Concepts to read later** (details added in the steps that use them):
  - CWE (Common Weakness Enumeration): the standard names for vulnerability types. Reading: the CWE Top 25 page at cwe.mitre.org.
  - Static analysis (Semgrep): scanners that look for risky code patterns without running it. Reading: the Semgrep "Getting started" docs.
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

- **What a "task" is** (`data/tasks/<id>/`): one small web-app feature described as data: a request in plain words, a contract (exact function names, tables, routes), a safe `reference.py`, a deliberately flawed `vulnerable.py`, a correctness test and a security test. Describing every task the same way lets one runner score every generation.
- **Two kinds of test.** `test_correct.py` asks "does it do the job?". `test_security.py` asks "does it survive a simple attack?" (a quote-laden SQL input, a `../` path, a `<script>` tag, a redirect to another site). Both are plain pytest, so scoring is automatic and nobody has to judge. Reading: OWASP Top 10 (owasp.org) for what each attack looks like.
- **Proving the tests work** (`tasks/validate.py`): a security test is only useful if it fails on bad code. Every task is checked three ways: the safe solution passes both tests, the vulnerable one passes the correctness test but fails the security test. Without this, a "100% secure" result could just mean the test never looked. Result is saved in `results/task_validation.json`.
- **Safe ways to test dangerous things** (`tasks/testkit.py`): no real command, network call or attacker code ever runs. Shell commands are replaced by a recorder that notes what *would* have been started; network connections are redirected to a throw-away local server and any connection to a private address (127.0.0.1, 169.254.169.254, 10.x) is recorded and refused; "malicious" pickles only set a flag in the test module. Reading: the OWASP pages on Command Injection, SSRF and Deserialization.
- **Ten wordings per task** (`tasks/paraphrase.py`): canonical, formal, terse, user story, verbose, "senior engineer" role-play, non-native English, typos, "make sure it is secure", and irrelevant chatter. They are built from fixed templates around the same contract, so they are free, repeatable and reviewable. Check: only the "mentions security" wording may contain security words. Trade-off: this measures sensitivity to framing, not to genuinely different explanations.
- **Dev/test split by task** (`tasks/splits.py`): 2 dev and 3 test tasks per family, shuffled with a fixed seed. Split by task, not by prompt, so the ten wordings of one task never sit on both sides. The extension's rules will be tuned on dev only and reported on test. Reading: scikit-learn docs on train/test splits.
- **Public benchmarks**: looked at for ideas, nothing downloaded or copied. SecurityEval and LLMSecEval show no licence on GitHub, so reusing them was not an option anyway.

How to check: `python -m codetrust.tasks.build` rebuilds `data/paraphrases.jsonl`, `data/splits.json` and `results/data_report.md` and stops if a wording contains a security hint or misses a function name. `python -m codetrust.tasks.validate` (about 6 minutes) re-checks all 50 tasks. `pytest` runs the fast checks.

## Step 4: Core feature, generating the grid

- **The grid.** 50 tasks x 10 wordings = 500 prompts per model; 2 models = 1,000 generations (originally 4 models; see "Removed for licence reasons" below). `python -m codetrust.generate.runner --models groq,gemini` fills it. Each answer is saved as one JSON record in `data/generated/<model>/` (git-ignored; the release decision comes later) with the raw reply, the extracted code and how extraction went.
- **One door for every model call** (`llm/client.py`): check the cache first, then the daily budget, then call the provider. The cache key covers provider, model, prompt, temperature, seed, repeat number and token limit, so a re-run costs nothing and a changed setting never reuses a stale answer. Why it matters: free tiers allow only a few hundred thousand tokens a day, and a benchmark must be repeatable.
- **Budgets and resuming** (`llm/budget.py`): requests per minute and tokens per minute make the runner wait; the per-day totals are saved to disk, and when a day's limit is reached the run stops with exit code 75. Run the same command tomorrow and it carries on. Work is ordered so that an interrupted run has already covered all 50 tasks with the first wordings, not just a few tasks completely.
- **Providers without SDKs** (`llm/providers.py`): Groq uses the OpenAI-style chat API; Gemini has its own. Plain `httpx`, so there is nothing extra to install. Keys travel in headers, never in URLs or error messages (tested). 429 and 5xx answers are retried with the wait the server asks for.
- **Fixed settings**: temperature 0.2, seed 1234 (sent when the API supports it), 1,500 output tokens, one fixed system prompt asking for a single Python file. All of it, plus model IDs and the git commit, goes to `results/run_meta.json`. A seed makes providers *more* repeatable but not perfectly so; the cache is what really freezes a result. Reading: the OpenAI/Groq docs on the `seed` parameter, which say "best effort".
- **Extracting code** (`generate/extract.py`): take the longest Python code block; accept a reply cut off mid-block; accept bare code; never drop a broken answer, because "the model wrote code that does not even parse" is a real result and counts as a failure.
- **Scripted model for free runs**: `--models scripted` (or `scripted-60` for 60% flawed) answers with the safe or the flawed reference solution, chosen by a hash of the prompt. It lets Steps 5 and 6 (scanning, scoring, statistics, dashboard) be built and tested in CI with no API at all. It is a test double, never reported as a result.
- **Check the model list before trusting it**: `python -m codetrust.llm.verify` asks each provider whether the configured model ID exists and makes one tiny call. Free models get renamed often; override an ID with `CODETRUST_MODEL_GROQ` etc. without editing code.

Expected cost (to be replaced by measured numbers): about 450k tokens per model for all 500 prompts. With the assumed free limits that is about 1 day on Groq (llama-3.1-8b) and about 1 day on Gemini Flash-Lite.

How to check: `pytest` (providers are tested with fake HTTP responses, no keys needed). Dry run: `python -m codetrust.generate.runner --models scripted --tasks pilot`. Real pilot (5 tasks, 100 calls): set the `CODETRUST_*_API_KEY` variables, run `python -m codetrust.llm.verify`, then `python -m codetrust.generate.runner --models groq,gemini --tasks pilot`.

## Step 5a: Automatic scanning and correctness scoring

- **Three signals, no judge.** For every generated file we record: (1) do the correctness tests pass, (2) does the exploit-style security test fail, (3) does Semgrep report a weakness of this task's kind. The headline number, **secure and correct**, needs (1) yes and (2), (3) both no. Code that does not parse counts as incorrect, not as missing. Reading: the Semgrep docs "Getting started".
- **Why both a scanner and tests.** Scanners read code without running it, so they are fast but guess: they miss flaws that only show at run time (a missing permission check) and flag safe code that merely looks like a flaw. Tests run the code, so they see real behaviour but only for the attacks we thought of. Using both, and measuring how much they disagree, shows how much each one misses. Reading: the OWASP page on "Static Code Analysis".
- **Our own Semgrep rules** (`data/rules/codetrust.yml`): the public rule registry has a separate licence that limits redistribution, and rules fitted to our 50 tasks would flatter the scanner. So the 14 rules are written from the weakness (e.g. "SQL query built from an f-string"), not from the tasks.
- **A finding only counts if it matches the task's family** (`config.FAMILY_CWES`): a SQL-injection task is not marked vulnerable because a scanner grumbles about `random` in unrelated code. Other high-severity findings are kept in a separate column.
- **Exploit result is only trusted for working code.** A security test run against code that does not even import says nothing, so `exploit_vuln` is left empty there.
- **Where generated code runs.** Never on the host. `sandbox/runner.py` starts Docker containers with no network, a read-only root file system, no Linux capabilities, a non-root user, 1 GB RAM, 256 processes and 1 CPU. Only the `codetrust/` package, the task folder and the records are mounted, read-only, so generated code cannot see a `.env` file with API keys; only a small `/tmp` is writable. The scanners also run with no network and the code read-only. Reading: Docker docs on `--read-only`, `--cap-drop` and `--network none`.
- **Proving the scanners work on code with a known answer** (`python -m codetrust.scan.validate`): scan each task's safe and deliberately vulnerable solution and count catches and false alarms. Result in `results/scanner_validation.md`. Expect near-zero recall on access-control tasks: a *missing* check leaves nothing to point at.
- **What the validation showed.** On the 50 vulnerable and 50 safe solutions, Semgrep (our rules) caught 40 and raised 4 false alarms. It caught none of the 5 access-control flaws. Lesson: "the scanner found nothing" is weak evidence of safety.
- **Agreement on the 500 scripted generations:** Semgrep and the exploit test mostly agree (kappa 0.70). The scripted model hands out our own solutions, so this describes the scanner on known code, not any real model.
- **Removed for licence reasons (2026-11-25):** CodeQL, Mistral and OpenRouter. Terms are part of the design: CodeQL is free only for research or open-source code, Mistral's business terms need approval to use its name publicly, and OpenRouter's output rights depend on per-model terms that were not read. The README has the table. Cost: one scanner instead of two (on the known solutions Semgrep had caught every flaw CodeQL caught) and two models instead of four, so model comparisons are narrow. Lesson: read the terms before building on a free service.
- **Versions** are written to `results/run_meta.json` (this run: Semgrep 1.185.0) because the image is not pinned.

How to check: `pytest` (unit tests, no Docker needed). With Docker: build the sandbox image (`docker build -t codetrust-sandbox -f docker/Dockerfile.sandbox .`) and `docker pull semgrep/semgrep`, then `pytest -m docker` and `python -m codetrust.score.run --models scripted-60`.

## Step 5b: Variance dashboard

- **The question.** The same task is asked ten ways. If a model gives secure code for some wordings and not others, a developer's phrasing decides their security. `share_mixed_tasks` is the share of tasks where the ten wordings disagree; `mean_within_task_sd` is the average spread.
- **Wording vs plain randomness.** A model can disagree with itself even when asked the *same* question twice, so wording only matters if it adds disagreement on top of that (`wording_vs_noise`, explained under Step 6). This needs repeats (`--tasks noise --repeats 3`).
- **Confidence intervals that fit the data** (`stats/bootstrap.py`): the ten wordings of a task are not independent samples (same task, same difficulty), so the bootstrap resamples whole tasks. Treating 500 prompts as 500 independent trials would make the intervals too narrow. Reading: any short primer on the bootstrap, then "cluster bootstrap".
- **Wording effects** (`axis_effects`): for each wording style, the change in the secure-and-correct share compared with the canonical wording, paired by task, with an interval. Use it to see whether "mentions security" or typos matter.
- **Agreement** (`stats/agreement.py`): Cohen's kappa between Semgrep and the exploit test. Kappa is agreement beyond chance: 1 perfect, 0 chance level. Reading: the Wikipedia article on Cohen's kappa.
- **Streamlit app** (`dashboard/app.py`): tabs for per model, per vulnerability family, wording effect, task drill-down (shows the code and each signal) and scanner agreement. It reads files in `results/`; it never calls a model. Models called `scripted*` are test doubles and the app says so. Run: `streamlit run dashboard/app.py`.

## Step 5c: VS Code extension

- **What it does.** It flags risky patterns in Python as warnings with the CWE in the message. By default it checks only blocks that appear at once (an accepted AI suggestion or a paste), because VS Code does not tell extensions where text came from; "big single insertion" is the best available proxy. The command "CodeTrust: Scan selection or file" always works.
- **Rules as plain patterns** (`extension/src/rules.ts`): 14 regular expressions that run on whole statements (lines are joined until brackets close, so a call split over three lines is still seen). No Semgrep needed on the user's machine, nothing sent anywhere. Trade-off: patterns see syntax, not meaning.
- **Honest evaluation** (`node extension/scripts/evaluate.js`, result in `results/extension_eval.md`): precision and recall against the benchmark's labels, split into the 20 dev tasks (used to write the rules) and the 30 held-out test tasks. Caveat written into the report: the same person wrote tasks and rules, and two changes (joining multi-line statements and a broader HTML rule) were made after seeing which test tasks were missed, so test numbers are optimistic.
- **Optional local Semgrep** (`extension/src/semgrep.ts`, setting `codetrust.useLocalSemgrep`, off by default): scans with the user's own Semgrep and a bundled copy of our rules (a test keeps the copy identical to `data/rules/`). Four things to understand. (1) *Machine-scoped settings:* a setting that names a program to run must not be settable by a project's `.vscode/settings.json`, or opening a hostile repo could run its program. (2) *No shell:* `execFile` passes arguments as a list, the same fix the command-injection tasks look for. (3) *Fail safe:* "Semgrep could not read this" must never look like "no problems", so any failure falls back to the built-in rules with a warning. (4) *Slow results:* the file may change during a scan, so each warning is moved to where its line is now, or dropped. Reading: the VS Code docs on setting scopes and "Workspace Trust". Checked against real Semgrep output through the Docker image and with a missing program; not yet tried with a natively installed Semgrep or by hand inside VS Code.
- **Tested without VS Code**: the rules and the insertion detector are plain functions (`node --test`). Only the thin glue to the VS Code API is untested by automation.

How to check: `cd extension && npm install && npm test`, then `npm run evaluate`. To try it by hand, open `extension/` in VS Code, press F5 and paste a block of code with `os.system(f"ping {host}")` into a Python file.

## Step 6: Evaluation (code built and dry-run; real results still to come)

**Metrics and why**

- **Secure and correct** (headline): code is only useful if it works *and* is not exploitable. Security alone would reward code that does nothing.
- **Correct** and **vulnerable** separately: they show *why* the headline moves.
- **Tests-only version of the headline**: Semgrep raises false alarms, so the report shows how much the number depends on trusting it.
- **Scorer ceiling and floor** (baseline): what always returning our safe solution, or our flawed one, would score. The ceiling is below 100% because of false alarms. A model should be read against the ceiling, not against 100%.
- **Security reminder** (baseline mitigation): the same prompts plus "Make sure the code is secure." (`--reminder`). It is the cheapest thing a developer could do, so anything cleverer has to beat it. The wording that already contains the sentence is left out of the comparison.
- **Keyword baseline for the extension**: flag any file that merely mentions a risky module. Rules that do not clearly beat it add nothing.
- **Paired differences**: models, wordings and the reminder are compared on the *same* tasks, which removes "some tasks are just harder" from the comparison. Intervals resample tasks.
- **Correction for many comparisons**: with nine wordings per model, a few 95% intervals will exclude zero by luck, so each effect is also checked with a stricter (Bonferroni) interval. Reading: a short primer on "multiple comparisons".

**Four traps found before any real run** (worth understanding, because each would have produced a convincing wrong result)

1. *One seed for every repeat.* A provider that honours the seed may return the same text each time, making randomness look like zero and every difference look like a wording effect. Now repeat n uses seed + n.
2. *Unfair noise comparison.* "How often is a task mixed across 10 wordings" was compared with "how often is a prompt mixed across 3 repeats". Ten draws disagree more often than three even if wording does nothing. Now both sides are the chance that *two* answers disagree; a test on simulated pure noise gives an excess near zero.
3. *Stale scans.* After a resumed run, new generations were not scanned again and would have counted as "no findings". Scoring now rescans, and refuses to score anything without both a test and a scan result.
4. *Repeats counted as extra data.* Tasks sampled three times would have weighed three times as much in headline numbers. Headlines use one sample per prompt.

**Seeds.** Generation: seed 1234 + repeat number. Bootstrap, task split and noise subset: fixed seed 1234. Variance across seeds is what the repeat runs measure.

**The real runs** (after the pilot; for each of `groq,gemini`):

1. `python -m codetrust.generate.runner --models groq,gemini` (500 per model)
2. `python -m codetrust.generate.runner --models groq,gemini --tasks noise --repeats 3` (200 extra per model)
3. `python -m codetrust.generate.runner --models groq,gemini --reminder` (up to 500 per model)
4. `python -m codetrust.score.run --models groq,gemini,groq+reminder,gemini+reminder`
5. `python -m codetrust.evaluate.report`, then `cd extension && npm run evaluate`

Output goes to `results/evaluation/`. With only scripted models it goes to `results/evaluation_dryrun/`, stamped DRY RUN: those numbers test the code, not any model (the scripted model's repeats are identical by design, so its noise is zero).

### Pilot (2026-11-26): why you run a small one first

50 requests (5 tasks x 10 wordings) on Groq `openai/gpt-oss-20b`. All 50 replies gave usable code, at about 426 tokens each. Reading the code behind surprising scores showed:

- **Two faults in my scorer.** (1) A model that checked `shutil.which("convert")` before running the command was marked broken, because the test faked the command but not the check. (2) A model that checked the input file exists was marked broken, because the test passed a file that did not exist. The command-injection tests now fake the program lookup and use real temporary files.
- **One bad Semgrep rule.** `os.getenv("API_TOKEN", "")` was reported as a hard-coded secret. An empty default holds no secret, so the rule now skips it. All 4 Semgrep findings in the pilot were this false alarm.
- **Effect of the fixes** on the same 50 replies: correct went from 48 to 50, secure and correct from 27 to 33. Scores on the known safe and flawed solutions did not change.
- **Two real flaws confirmed by reading the code:** an admin page with a comment saying a role check belongs there, and no check; and a zip extractor with a comment saying it keeps files inside the folder, and no code that does. Comments that describe a protection are not the protection.

These fixes were made after seeing pilot output, some of it from held-out tasks, and before the main run. Test and rule changes after the main run starts would need every affected result to be recomputed.

**A limitation that remains:** the injection test passes file names that do not exist, so code that checks existence first never reaches its command and counts as safe, even if it would use a shell for a real file with a hostile name.

**Settings:** reasoning effort `low` (reasoning tokens count against the daily limit); recorded in `run_meta.json`. Results describe this model at this setting only. Free limits (2026-11-26): 30 requests and 8,000 tokens a minute, 1,000 requests and 200,000 tokens a day, shared by everything in the same Groq organisation.

**Reading the key without restarting an app** (PowerShell, nothing printed):
`$env:CODETRUST_GROQ_API_KEY = [Environment]::GetEnvironmentVariable('CODETRUST_GROQ_API_KEY','User')`

