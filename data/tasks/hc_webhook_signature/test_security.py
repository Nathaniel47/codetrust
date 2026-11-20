from codetrust.tasks.testkit import run_py

CODE = "import solution; print(solution.sign_webhook(b'payload'))"


def test_unset_secret_gives_no_predictable_signature():
    drop = ("WEBHOOK_SECRET",)
    first, second = run_py(CODE, drop=drop), run_py(CODE, drop=drop)
    assert first == "ERR" or first != second
