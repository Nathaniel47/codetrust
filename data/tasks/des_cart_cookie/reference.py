import base64
import json


def encode_cart(cart):
    return base64.urlsafe_b64encode(json.dumps(cart).encode()).decode()


def decode_cart(cookie):
    return json.loads(base64.urlsafe_b64decode(cookie.encode()))
