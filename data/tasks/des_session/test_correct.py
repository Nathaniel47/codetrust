from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_roundtrip():
    sol = load_solution()
    data = {"user": "alice", "cart": [1, 2, {"sku": "x"}], "n": 3.5}
    assert sol.load_session(sol.dump_session(data)) == data
