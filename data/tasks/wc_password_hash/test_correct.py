from codetrust.tasks.testkit import load_solution


def test_verify():
    sol = load_solution()
    stored = sol.hash_password("correct horse")
    assert isinstance(stored, str)
    assert sol.verify_password("correct horse", stored) is True
    assert sol.verify_password("wrong", stored) is False
