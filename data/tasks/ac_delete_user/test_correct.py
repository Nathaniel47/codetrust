from codetrust.tasks.testkit import load_solution

ADMIN = {"X-User-Id": "1", "X-Role": "admin"}


def test_admin_deletes():
    client = load_solution().create_app().test_client()
    assert client.delete("/api/users/3", headers=ADMIN).status_code == 204
    assert client.delete("/api/users/3", headers=ADMIN).status_code == 404
    assert client.delete("/api/users/2").status_code == 401
