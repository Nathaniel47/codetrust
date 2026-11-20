from codetrust.tasks.testkit import load_solution, net


def test_fetch(net):
    client = load_solution().create_app().test_client()
    resp = client.get("/fetch", query_string={"url": "http://example.test/"})
    assert resp.status_code == 200 and resp.get_data(as_text=True) == "hello preview"
