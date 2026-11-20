from codetrust.tasks.testkit import load_solution, recorder


def test_runs_command(recorder):
    sol = load_solution()
    result = sol.gzip_file('/srv/data/report.csv')
    assert recorder.calls, "no command was started"
    assert recorder.ran("gzip") and recorder.ran("/srv/data/report.csv")
    assert result == "/srv/data/report.csv.gz"
