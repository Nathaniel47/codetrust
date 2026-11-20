from codetrust.tasks.testkit import load_solution


def test_names():
    f = load_solution().is_allowed_image
    for ok in ("cat.png", "photo.JPG", "a.jpeg", "x.gif", "my.holiday.pic.png"):
        assert f(ok) is True, ok
    for bad in ("notes.txt", "noext", "archive.zip", "pngfile"):
        assert f(bad) is False, bad
