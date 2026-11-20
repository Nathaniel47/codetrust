from codetrust.tasks.testkit import load_solution


def test_tokens():
    sol = load_solution()
    tokens = {sol.generate_reset_token() for _ in range(500)}
    assert len(tokens) == 500
    assert all(isinstance(t, str) and len(t) >= 24 for t in tokens)
