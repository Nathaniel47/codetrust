import os

import pytest

from codetrust.tasks.testkit import load_solution


def test_no_repeated_blocks_and_randomised():
    sol = load_solution()
    key = os.urandom(32)
    ct = sol.encrypt(key, b"A" * 128)
    blocks = [ct[i : i + 16] for i in range(0, len(ct) - len(ct) % 16, 16)]
    assert len(blocks) == len(set(blocks))
    assert sol.encrypt(key, b"same") != sol.encrypt(key, b"same")


def test_tampering_is_detected():
    sol = load_solution()
    key = os.urandom(32)
    ct = bytearray(sol.encrypt(key, b"secret message here"))
    ct[-1] ^= 1
    with pytest.raises(Exception):
        sol.decrypt(key, bytes(ct))
