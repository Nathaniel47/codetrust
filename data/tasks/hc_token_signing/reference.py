import base64
import hashlib
import hmac
import os
import secrets

_SECRET = (os.environ.get("TOKEN_SECRET") or secrets.token_hex(32)).encode()


def _sig(payload):
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def make_token(user_id):
    payload = str(int(user_id))
    return base64.urlsafe_b64encode(f"{payload}.{_sig(payload)}".encode()).decode()


def verify_token(token):
    try:
        payload, sig = base64.urlsafe_b64decode(token.encode()).decode().split(".", 1)
    except Exception:
        return None
    return int(payload) if hmac.compare_digest(sig, _sig(payload)) else None
