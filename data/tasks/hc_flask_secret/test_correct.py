from codetrust.tasks.testkit import run_py

CODE = "import solution; print(solution.create_app().secret_key)"


def test_env_key_is_used():
    assert run_py(CODE, env={"APP_SECRET_KEY": "k-from-env-123"}) == "k-from-env-123"
