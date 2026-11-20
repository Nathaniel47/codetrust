import hashlib
import hmac


def sign_message(key, message):
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def verify_signature(key, message, signature):
    return hmac.compare_digest(sign_message(key, message), signature)
