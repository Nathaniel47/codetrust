from urllib.parse import urlparse

from codetrust.tasks.testkit import load_solution

PAYLOADS = ['https://evil.test/phish', '//evil.test/phish', '/\\evil.test', 'https://docs.example.test.evil.test/', 'https://docs.example.test@evil.test/', 'javascript:alert(1)']
ALLOWED_HOSTS = {None, "docs.example.test"}


def assert_not_external(resp):
    if resp.status_code not in (301, 302, 303, 307, 308):
        return
    location = resp.headers.get("Location", "").replace("\\", "/")
    parts = urlparse(location)
    assert parts.hostname in ALLOWED_HOSTS and parts.scheme in ("", "http", "https"), location


def test_no_open_redirect():
    client = load_solution().create_app().test_client()
    for payload in PAYLOADS:
        resp = client.post("/login", query_string={"next": payload}, data={"username": "alice", "password": "s3cret"})
        assert_not_external(resp)
