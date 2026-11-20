import hashlib
import hmac
import os


def sign_webhook(body):
    secret = os.environ.get("WEBHOOK_SECRET", "whsec_default").encode()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()
