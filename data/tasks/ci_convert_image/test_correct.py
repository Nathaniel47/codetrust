from codetrust.tasks.testkit import load_solution, recorder


def test_runs_command(recorder):
    sol = load_solution()
    result = sol.convert_image('photo.png', 'out.jpg')
    assert recorder.calls, "no command was started"
    assert recorder.ran("convert") and recorder.ran("photo.png") and recorder.ran("out.jpg")
    assert result is True
