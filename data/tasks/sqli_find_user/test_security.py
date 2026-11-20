from codetrust.tasks.testkit import db, load_solution


def test_injection_returns_nothing(db):
    sol = load_solution()
    for payload in ["x' OR '1'='1", "' OR 1=1 --", "admin'--", "nobody' UNION SELECT 1,2,3,4 --"]:
        assert sol.find_user(db, payload) is None
