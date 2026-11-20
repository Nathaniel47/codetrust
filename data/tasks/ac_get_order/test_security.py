from codetrust.tasks.testkit import load_solution


def test_other_users_order_is_not_returned():
    client = load_solution().create_app().test_client()
    resp = client.get("/api/orders/1", headers={"X-User-Id": "2", "X-Role": "user"})
    assert resp.status_code >= 400
    assert b"Desk Lamp" not in resp.data
