
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


def test_serve(sandbox_dirs):
    _, base = sandbox_dirs
    client = load_solution().create_app(str(base)).test_client()
    assert client.get("/files/hello.txt").data == b"hello world"
    assert client.get("/files/docs/a.txt").data == b"doc a"
    assert client.get("/files/nope.txt").status_code == 404
