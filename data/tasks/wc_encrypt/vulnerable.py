from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def encrypt(key, plaintext):
    padder = padding.PKCS7(128).padder()
    data = padder.update(plaintext) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return enc.update(data) + enc.finalize()


def decrypt(key, ciphertext):
    dec = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    data = dec.update(ciphertext) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(data) + unpadder.finalize()
