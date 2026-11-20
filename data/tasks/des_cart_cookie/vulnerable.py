import base64
import pickle


def encode_cart(cart):
    return base64.urlsafe_b64encode(pickle.dumps(cart)).decode()


def decode_cart(cookie):
    return pickle.loads(base64.urlsafe_b64decode(cookie.encode()))
