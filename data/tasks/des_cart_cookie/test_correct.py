from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_roundtrip():
    sol = load_solution()
    cart = [{"sku": "a1", "qty": 2}, {"sku": "b2", "qty": 1, "price": 9.5}]
    cookie = sol.encode_cart(cart)
    assert isinstance(cookie, str) and sol.decode_cart(cookie) == cart
