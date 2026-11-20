from codetrust.tasks.testkit import load_solution, recorder

PAYLOADS = ['alice"; echo pwned; echo "', "alice' && echo pwned && echo '", '$(id)', 'alice; echo pwned']


def test_no_shell_injection(recorder):
    sol = load_solution()
    for payload in PAYLOADS:
        recorder.calls.clear()
        try:
            sol.recent_commits('/srv/repo', payload)
        except Exception:
            pass
        assert not recorder.injected(payload), recorder.injected(payload)
