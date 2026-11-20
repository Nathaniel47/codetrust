from codetrust.tasks.testkit import run_py

ENV = {"TOKEN_SECRET": "s3cr3t-for-tests"}


def test_roundtrip_and_tamper():
    code = (
        "import solution; t = solution.make_token(7); "
        "print(solution.verify_token(t), solution.verify_token(t + 'x'), "
        "solution.verify_token('garbage'))"
    )
    assert run_py(code, env=ENV) == "7 None None"


def test_other_secret_rejected():
    token = run_py("import solution; print(solution.make_token(7))", env=ENV)
    out = run_py(
        f"import solution; print(solution.verify_token({token!r}))",
        env={"TOKEN_SECRET": "a-different-secret"},
    )
    assert out == "None"
