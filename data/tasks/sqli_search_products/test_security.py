from codetrust.tasks.testkit import db, load_solution


def test_injection_returns_nothing(db):
    sol = load_solution()
    for payload in ["zzz' OR '1'='1", "%' OR 1=1 --", "zzz' UNION SELECT username FROM users --"]:
        assert sol.search_products(db, payload) == []
