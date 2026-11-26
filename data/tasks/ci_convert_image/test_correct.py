from codetrust.tasks.testkit import load_solution, recorder


def test_runs_command(recorder, tmp_path, monkeypatch):
    sol = load_solution()  # reads solution.py from the current folder, so load before moving
    monkeypatch.chdir(tmp_path)
    (tmp_path / "photo.png").write_bytes(b"image")
    result = sol.convert_image('photo.png', 'out.jpg')
    assert recorder.calls, "no command was started"
    assert recorder.ran("convert") and recorder.ran("photo.png") and recorder.ran("out.jpg")
    assert result is True
