from codetrust.tasks.testkit import load_solution


def test_hello():
    client = load_solution().create_app().test_client()
    assert client.get("/hello?name=Ann").data == b"<h1>Hello, Ann!</h1>"
    assert client.get("/hello").data == b"<h1>Hello, world!</h1>"
