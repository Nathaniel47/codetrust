import hashlib
import hmac
import os


def sign_webhook(body):
    secret = os.environ["WEBHOOK_SECRET"].encode()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()
