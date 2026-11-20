from codetrust.tasks.testkit import load_solution


def test_owner_reads_order():
    client = load_solution().create_app().test_client()
    resp = client.get("/api/orders/1", headers={"X-User-Id": "1", "X-Role": "user"})
    assert resp.status_code == 200 and resp.get_json()["item"] == "Desk Lamp"


def test_missing_and_unauthenticated():
    client = load_solution().create_app().test_client()
    assert client.get("/api/orders/1").status_code == 401
    assert client.get("/api/orders/99", headers={"X-User-Id": "1"}).status_code == 404
