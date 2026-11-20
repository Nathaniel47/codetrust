import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(key, plaintext):
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)


def decrypt(key, ciphertext):
    return AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], None)
