
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


def test_no_escape(sandbox_dirs):
    root, base = sandbox_dirs
    sol = load_solution()
    for name in ["../secret.txt", "docs/../../secret.txt", str(root / "secret.txt")]:
        try:
            text = sol.read_public_file(str(base), name)
        except Exception:
            continue
        assert "TOP-SECRET" not in text
