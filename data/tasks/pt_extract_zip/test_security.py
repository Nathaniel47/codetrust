import zipfile

from codetrust.tasks.testkit import load_solution


def test_zip_slip(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("ok.txt", "fine")
        zf.writestr("../evil.txt", "pwned")
        zf.writestr("sub/../../evil2.txt", "pwned")
    dest = tmp_path / "out"
    dest.mkdir()
    try:
        load_solution().extract_archive(str(archive), str(dest))
    except Exception:
        pass
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path / "evil2.txt").exists()
