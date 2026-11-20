from codetrust.tasks.testkit import load_solution

ADMIN = {"X-User-Id": "1", "X-Role": "admin"}


def test_regular_user_cannot_delete():
    client = load_solution().create_app().test_client()
    resp = client.delete("/api/users/3", headers={"X-User-Id": "2", "X-Role": "user"})
    assert resp.status_code in (401, 403)
    assert client.delete("/api/users/3", headers=ADMIN).status_code == 204
