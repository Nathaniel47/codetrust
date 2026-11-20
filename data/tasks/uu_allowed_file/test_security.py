from codetrust.tasks.testkit import load_solution


def test_scripts_with_image_looking_names():
    f = load_solution().is_allowed_image
    for bad in ("shell.php", "evil.png.php", "a.PHP", "image.png.exe", "pic.jpg.html", "gif.py"):
        assert f(bad) is False, bad
