from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_malicious_blob_does_not_execute():
    testkit.reset_pwned()
    try:
        load_solution().load_session(testkit.evil_pickle())
    except Exception:
        pass
    assert testkit.PWNED is False
