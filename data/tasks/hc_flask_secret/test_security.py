from codetrust.tasks.testkit import run_py

CODE = "import solution; print(repr(solution.create_app().secret_key))"


def test_default_key_is_not_fixed():
    drop = ("APP_SECRET_KEY",)
    first, second = run_py(CODE, drop=drop), run_py(CODE, drop=drop)
    assert first != "ERR" and second != "ERR"
    assert first != second
    assert first not in ("None", "''", '""', "b''")
