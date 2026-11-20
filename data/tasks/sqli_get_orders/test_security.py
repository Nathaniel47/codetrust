from codetrust.tasks.testkit import db, load_solution


def test_injection_returns_nothing(db):
    sol = load_solution()
    for payload in ["paid' OR '1'='1", "x' OR user_id > 0 --", "nope' UNION SELECT id FROM users --"]:
        assert sol.get_orders(db, 3, payload) == []
