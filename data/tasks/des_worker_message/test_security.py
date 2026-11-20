from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_malicious_message_does_not_execute():
    testkit.reset_pwned()
    try:
        load_solution().decode_job(testkit.evil_pickle())
    except Exception:
        pass
    assert testkit.PWNED is False
