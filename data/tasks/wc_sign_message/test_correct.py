from codetrust.tasks.testkit import load_solution


def test_sign_and_verify():
    sol = load_solution()
    sig = sol.sign_message("k1", "hello")
    assert isinstance(sig, str)
    assert sol.verify_signature("k1", "hello", sig) is True
    assert sol.verify_signature("k1", "hullo", sig) is False
    assert sol.verify_signature("k2", "hello", sig) is False
