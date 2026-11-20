"""Pull the Python code out of a model reply. One deterministic rule, with failures counted."""

import ast
import re

FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\r?\n(.*?)```", re.DOTALL)


def extract_code(reply: str) -> tuple[str | None, str]:
    """Return (code, status). Status: ok, no_code, syntax_error.

    Rule: take the longest fenced block tagged python/py (or untagged). If there is no fence, take
    the whole reply when it parses as Python. A block that does not parse is returned with status
    syntax_error so it is still scored (as a functional failure), not dropped.
    """
    blocks = [code for lang, code in FENCE.findall(reply) if lang.lower() in ("python", "py", "")]
    if not blocks:
        # An unterminated fence (reply cut off by the token limit): take what follows the opener.
        opener = re.search(r"```[ \t]*(?:python|py)?[ \t]*\r?\n", reply, re.IGNORECASE)
        if opener:
            blocks = [reply[opener.end() :]]
    candidate = max(blocks, key=len) if blocks else reply.strip() + "\n"
    if not candidate.strip():
        return None, "no_code"
    try:
        ast.parse(candidate)
    except SyntaxError:
        return (candidate, "syntax_error") if blocks else (None, "no_code")
    return candidate, "ok"
