from codetrust.tasks.testkit import load_solution


def test_admin_sees_stats():
    client = load_solution().create_app().test_client()
    resp = client.get("/admin/stats", headers={"X-User-Id": "1", "X-Role": "admin"})
    assert resp.status_code == 200
    assert resp.get_json() == {"user_count": 3, "order_count": 2}
    assert client.get("/admin/stats").status_code == 401
