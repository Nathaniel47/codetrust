from codetrust.tasks.testkit import load_solution


def test_regular_user_gets_nothing():
    client = load_solution().create_app().test_client()
    resp = client.get("/admin/stats", headers={"X-User-Id": "2", "X-Role": "user"})
    assert resp.status_code >= 400
    assert b"user_count" not in resp.data
