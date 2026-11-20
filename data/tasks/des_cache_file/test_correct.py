from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_roundtrip(tmp_path):
    sol = load_solution()
    path = str(tmp_path / "entry.cache")
    obj = {"k": [1, 2, 3], "name": "x", "nested": {"a": 1.5}}
    sol.save_cache_entry(path, obj)
    assert sol.load_cache_entry(path) == obj
