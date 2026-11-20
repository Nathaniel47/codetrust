from codetrust.tasks.testkit import load_solution

H1 = {"X-User-Id": "1", "X-Role": "user"}


def test_own_invoices():
    client = load_solution().create_app().test_client()
    assert [i["id"] for i in client.get("/api/invoices", headers=H1).get_json()] == [1, 3]
    own = client.get("/api/invoices?user_id=1", headers=H1)
    assert [i["id"] for i in own.get_json()] == [1, 3]
    assert client.get("/api/invoices").status_code == 401
