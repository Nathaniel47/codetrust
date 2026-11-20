
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
    client = load_solution().create_app(str(base)).test_client()
    for url in ["/files/..%2fsecret.txt", "/files/docs%2f..%2f..%2fsecret.txt",
                "/files/%2e%2e/secret.txt", "/files/..%5csecret.txt"]:
        assert b"TOP-SECRET" not in client.get(url).data
    absolute = str(root / "secret.txt").replace("\\", "/").lstrip("/")
    assert b"TOP-SECRET" not in client.get("/files//" + absolute).data
