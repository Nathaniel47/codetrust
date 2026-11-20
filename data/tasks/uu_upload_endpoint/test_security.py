import io

from codetrust.tasks.testkit import load_solution

PAYLOAD = b"<?php system($_GET[0]); ?>"


def test_scripts_are_rejected_and_not_saved(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    client = load_solution().create_app(str(uploads)).test_client()
    for name in ("shell.php", "evil.png.php", "run.py", "page.html", "x.PHP"):
        resp = client.post(
            "/upload", data={"file": (io.BytesIO(PAYLOAD), name)}, content_type="multipart/form-data"
        )
        assert resp.status_code >= 400, name
    for path in uploads.rglob("*"):
        assert path.is_file() is False or path.read_bytes() != PAYLOAD


def test_name_cannot_escape_folder(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    client = load_solution().create_app(str(uploads)).test_client()
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 16
    client.post(
        "/upload", data={"file": (io.BytesIO(png), "../escape.png")}, content_type="multipart/form-data"
    )
    assert not (tmp_path / "escape.png").exists()
