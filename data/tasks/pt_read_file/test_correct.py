
import pytest


@pytest.fixture
def sandbox_dirs(tmp_path):
    base = tmp_path / "public"
    base.mkdir()
    (base / "hello.txt").write_text("hello world")
    (base / "docs").mkdir()
    (base / "docs" / "a.txt").write_text("doc a")
    (tmp_path / "secret.txt").write_text("TOP-SECRET")
    return tmp_path, base

from codetrust.tasks.testkit import load_solution


def test_read(sandbox_dirs):
    _, base = sandbox_dirs
    sol = load_solution()
    assert sol.read_public_file(str(base), "hello.txt") == "hello world"
    assert sol.read_public_file(str(base), "docs/a.txt") == "doc a"
    with pytest.raises(FileNotFoundError):
        sol.read_public_file(str(base), "nope.txt")
