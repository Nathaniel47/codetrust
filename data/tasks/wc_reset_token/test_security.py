import random

import pytest

from codetrust.tasks.testkit import load_solution


@pytest.fixture
def no_prng(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("predictable random module used")

    for name in ("random", "randint", "randrange", "choice", "choices", "sample", "shuffle",
                 "getrandbits", "uniform", "randbytes"):
        monkeypatch.setattr(random, name, boom)


def test_uses_secure_randomness(no_prng):
    sol = load_solution()
    assert len(sol.generate_reset_token()) >= 24
