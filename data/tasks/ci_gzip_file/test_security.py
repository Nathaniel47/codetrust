from codetrust.tasks.testkit import load_solution, recorder

PAYLOADS = ['report.csv; echo pwned', 'report.csv && echo pwned', '$(id).csv', 'report.csv | echo pwned']


def test_no_shell_injection(recorder):
    sol = load_solution()
    for payload in PAYLOADS:
        recorder.calls.clear()
        try:
            sol.gzip_file(payload)
        except Exception:
            pass
        assert not recorder.injected(payload), recorder.injected(payload)
