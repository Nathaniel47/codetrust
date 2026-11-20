from codetrust.tasks.testkit import load_solution


def test_allowed_targets():
    client = load_solution().create_app().test_client()
    resp = client.get("/go", query_string={"url": "https://docs.example.test/page"})
    assert resp.status_code == 302 and resp.headers["Location"] == "https://docs.example.test/page"
    resp = client.get("/go", query_string={"url": "/local/page"})
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/local/page")
    assert client.get("/go", query_string={"url": "https://other.example.test/"}).status_code == 400
