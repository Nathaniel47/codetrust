import hashlib

from codetrust.tasks.testkit import load_solution


def test_salted_and_not_plain_digest():
    sol = load_solution()
    first, second = sol.hash_password("hunter2"), sol.hash_password("hunter2")
    assert first != second
    for algo in ("md5", "sha1", "sha256"):
        assert first != hashlib.new(algo, b"hunter2").hexdigest()
