from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_roundtrip():
    sol = load_solution()
    assert sol.decode_job(sol.encode_job("resize", {"w": 10, "path": "a.png"})) == (
        "resize",
        {"w": 10, "path": "a.png"},
    )
