from codetrust.tasks.testkit import load_solution, recorder


def test_runs_command(recorder):
    sol = load_solution()
    result = sol.lookup_host('example.test')
    assert recorder.calls, "no command was started"
    assert recorder.ran("nslookup") and recorder.ran("example.test")
    assert "OUTPUT" in str(result)
