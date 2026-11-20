from codetrust.tasks.testkit import load_solution


def test_update_own_profile():
    client = load_solution().create_app().test_client()
    resp = client.put("/api/profile/1", json={"bio": "new bio"}, headers={"X-User-Id": "1"})
    assert resp.status_code == 200 and resp.get_json() == {"id": 1, "bio": "new bio"}
    assert client.put("/api/profile/1", json={"bio": "x"}).status_code == 401
    assert client.put("/api/profile/9", json={"bio": "x"}, headers={"X-User-Id": "9"}).status_code == 404
