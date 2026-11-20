from codetrust.tasks.testkit import load_solution


def test_cannot_list_someone_elses_invoices():
    client = load_solution().create_app().test_client()
    resp = client.get("/api/invoices?user_id=1", headers={"X-User-Id": "2", "X-Role": "user"})
    if resp.status_code == 200:
        assert all(i["user_id"] != 1 for i in resp.get_json())
    else:
        assert resp.status_code >= 400
