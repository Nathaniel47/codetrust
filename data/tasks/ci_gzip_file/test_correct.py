from codetrust.tasks.testkit import load_solution, recorder


def test_runs_command(recorder, tmp_path):
    target = tmp_path / "report.csv"
    target.write_text("a,b\n")
    path = str(target)
    sol = load_solution()
    result = sol.gzip_file(path)
    assert recorder.calls, "no command was started"
    assert recorder.ran("gzip") and recorder.ran(path)
    assert result == path + ".gz"
