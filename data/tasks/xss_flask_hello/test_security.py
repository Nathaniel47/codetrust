from codetrust.tasks.testkit import XSS_PAYLOADS, load_solution


def test_payloads_are_neutralised():
    client = load_solution().create_app().test_client()
    for payload in XSS_PAYLOADS:
        body = client.get("/hello", query_string={"name": payload}).get_data(as_text=True)
        assert payload not in body
        assert "<script" not in body.lower() and "<img" not in body.lower()
