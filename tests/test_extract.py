from codetrust.generate.extract import extract_code


def test_plain_fenced_block():
    assert extract_code("Here:\n```python\nx = 1\n```\nDone") == ("x = 1\n", "ok")


def test_longest_block_wins_and_untagged_counts():
    reply = "```python\na = 1\n```\n```\nb = 2\nc = 3\n```"
    assert extract_code(reply) == ("b = 2\nc = 3\n", "ok")


def test_other_languages_are_ignored():
    code, status = extract_code("```bash\npip install flask\n```\n```py\ny = 2\n```")
    assert (code, status) == ("y = 2\n", "ok")


def test_unterminated_fence_from_cut_off_reply():
    code, status = extract_code("```python\nx = 1\ny = 2\n")
    assert status == "ok" and code.startswith("x = 1")


def test_bare_code_without_fence():
    assert extract_code("def f():\n    return 1\n") == ("def f():\n    return 1\n", "ok")


def test_prose_only_is_no_code():
    assert extract_code("Sorry, I cannot help with that.") == (None, "no_code")
    assert extract_code("") == (None, "no_code")


def test_broken_code_is_kept_but_flagged():
    code, status = extract_code("```python\ndef broken(:\n```")
    assert status == "syntax_error" and "broken" in code
