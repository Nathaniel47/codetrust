
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


def test_list(sandbox_dirs):
    _, base = sandbox_dirs
    sol = load_solution()
    assert sol.list_directory(str(base), "") == ["docs", "hello.txt"]
    assert sol.list_directory(str(base), "docs") == ["a.txt"]
