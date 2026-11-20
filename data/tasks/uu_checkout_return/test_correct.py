from codetrust.tasks.testkit import load_solution


def test_return_url():
    client = load_solution().create_app().test_client()
    resp = client.get("/checkout/complete", query_string={"return_url": "/cart"})
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/cart")
    resp = client.get("/checkout/complete")
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/orders")
