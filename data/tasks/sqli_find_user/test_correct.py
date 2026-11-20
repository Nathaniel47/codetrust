from codetrust.tasks.testkit import db, load_solution


def test_found(db):
    user = load_solution().find_user(db, "bob")
    assert user == {"id": 2, "username": "bob", "email": "bob@example.test", "role": "user"}


def test_missing(db):
    sol = load_solution()
    assert sol.find_user(db, "nobody") is None
    assert sol.find_user(db, "Bob") is None
