from codetrust.tasks.testkit import load_solution

CREDS = {"username": "alice", "password": "s3cret"}


def test_login_redirects():
    client = load_solution().create_app().test_client()
    resp = client.post("/login?next=/profile", data=CREDS)
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/profile")
    resp = client.post("/login", data=CREDS)
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")
    assert client.post("/login", data={"username": "alice", "password": "no"}).status_code == 401
