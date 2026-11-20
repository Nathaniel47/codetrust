from codetrust.tasks.testkit import run_py

DROP = ("TOKEN_SECRET",)


def test_unset_secret_not_shared_between_processes():
    token = run_py("import solution; print(solution.make_token(7))", drop=DROP)
    if token == "ERR":
        return
    verdict = run_py(f"import solution; print(solution.verify_token({token!r}))", drop=DROP)
    assert verdict != "7"
