# CodeTrust for VS Code

Flags risky patterns in AI-generated Python code as soon as it lands in your editor.

- **What it flags:** 14 rules for SQL built from strings, HTML built without escaping, shell commands, hard-coded secrets, weak hashes and ECB mode, predictable `random` for tokens, unsafe `pickle`/`yaml.load`, requests to variable URLs, redirects taken from the request, upload names used as-is, and file paths built from input. Each warning names its CWE.
- **When:** by default only for blocks that appear at once (an accepted suggestion or a paste), so your own typing is left alone. Set `codetrust.scope` to `file` to rescan the whole file on every change. The command **CodeTrust: Scan selection or file** always works.
- **Private:** the rules run inside the extension. No code, file name or usage data is sent anywhere.

The rules come from the CodeTrust benchmark, which measures how secure LLM-written code is and how much that changes with wording. They are patterns, not a full analyser: they read one statement at a time and cannot follow data flow or notice a missing permission check. Precision and recall on held-out tasks are in the repository (`results/extension_eval.md`).
