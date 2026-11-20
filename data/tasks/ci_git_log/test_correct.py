from codetrust.tasks.testkit import load_solution, recorder


def test_runs_command(recorder):
    sol = load_solution()
    result = sol.recent_commits('/srv/repo', 'alice')
    assert recorder.calls, "no command was started"
    assert recorder.ran("git") and recorder.ran("log") and recorder.ran("alice")
    assert isinstance(result, list) and len(result) == 2 and all("OUTPUT" in line for line in result)
