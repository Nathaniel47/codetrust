from codetrust.tasks.testkit import load_solution


def test_format():
    sol = load_solution()
    codes = [sol.generate_otp() for _ in range(200)]
    assert all(isinstance(c, str) and len(c) == 6 and c.isdigit() for c in codes)
    assert len(set(codes)) > 100
