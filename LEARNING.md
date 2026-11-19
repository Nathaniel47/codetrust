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
