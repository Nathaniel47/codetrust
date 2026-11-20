import hashlib


def sign_message(key, message):
    return hashlib.md5((key + message).encode()).hexdigest()


def verify_signature(key, message, signature):
    return sign_message(key, message) == signature
