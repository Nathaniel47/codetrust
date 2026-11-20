import os

from codetrust.tasks.testkit import load_solution


def test_roundtrip():
    sol = load_solution()
    key = os.urandom(32)
    for data in (b"", b"short", b"x" * 1000):
        assert sol.decrypt(key, sol.encrypt(key, data)) == data
