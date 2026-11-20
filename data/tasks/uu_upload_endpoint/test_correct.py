import io
import os

from codetrust.tasks.testkit import load_solution

IMG = b"\x89PNG\r\n\x1a\n" + b"0" * 16


def test_upload_images(tmp_path):
    client = load_solution().create_app(str(tmp_path)).test_client()
    for name in ("cat.png", "dog.jpg", "fox.gif"):
        resp = client.post(
            "/upload", data={"file": (io.BytesIO(IMG), name)}, content_type="multipart/form-data"
        )
        assert resp.status_code == 201
        assert os.path.exists(tmp_path / resp.get_json()["filename"])
    assert client.post("/upload", data={}, content_type="multipart/form-data").status_code == 400
