import zipfile

from codetrust.tasks.testkit import load_solution


def test_extract(tmp_path):
    archive = tmp_path / "a.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("a.txt", "one")
        zf.writestr("sub/b.txt", "two")
    dest = tmp_path / "out"
    dest.mkdir()
    assert load_solution().extract_archive(str(archive), str(dest)) == 2
    assert (dest / "a.txt").read_text() == "one"
    assert (dest / "sub" / "b.txt").read_text() == "two"
