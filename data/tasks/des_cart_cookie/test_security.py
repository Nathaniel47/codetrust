from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution

import base64


def test_malicious_cookie_does_not_execute():
    testkit.reset_pwned()
    for raw in (base64.urlsafe_b64encode(testkit.evil_pickle()), base64.b64encode(testkit.evil_pickle())):
        try:
            load_solution().decode_cart(raw.decode())
        except Exception:
            pass
    assert testkit.PWNED is False
