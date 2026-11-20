import hashlib


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(password, stored):
    return hashlib.md5(password.encode()).hexdigest() == stored
