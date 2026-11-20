from codetrust.tasks.testkit import load_solution


def test_cannot_edit_someone_elses_profile():
    client = load_solution().create_app().test_client()
    resp = client.put(
        "/api/profile/1", json={"bio": "HACKED"}, headers={"X-User-Id": "2", "X-Role": "user"}
    )
    assert resp.status_code >= 400
    assert b"HACKED" not in resp.data
