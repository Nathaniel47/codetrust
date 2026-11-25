# CLAUDE.md: CodeTrust coding rules

- Follow PLAN.md; if anything conflicts, PLAN.md wins. Work one BUILD_STEPS.md step at a time.
- Python 3.11, no LangChain/LlamaIndex/LangGraph. Keep the generation, scanning and scoring stages as separate, plainly written modules.
- Secrets only from environment variables named `CODETRUST_*`. Never commit `.env`; `.env.example` has names with empty values.
- Generated code is only ever analysed (Semgrep) or run inside the sandbox, never against real services, real networks or real personal data. Test data is synthetic.
- Scoring is automatic (static analysers, unit tests, exploit-style security tests). No LLM judge.
- Every LLM call goes through the cached client in `codetrust/llm/`. Fixed seeds; record model IDs, temperature, seed and git commit in `results/run_meta.json`.
- Format and lint with ruff (line length 100). Write tests in `tests/` for every feature; run `pytest` before each commit.
- Code comments only for non-obvious reasons. Plain-English explanations go in LEARNING.md, not chat.
- Commit with the step name in the message, then push (only once a remote exists and the user has approved it). Never add attribution to commits or PRs: no `Co-Authored-By` lines and no "Generated with" text.
