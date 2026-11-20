import hashlib
import hmac

from codetrust.tasks.testkit import load_solution


def test_signature(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "abc")
    expected = hmac.new(b"abc", b"payload", hashlib.sha256).hexdigest()
    assert load_solution().sign_webhook(b"payload") == expected
