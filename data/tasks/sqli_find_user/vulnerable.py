def find_user(conn, username):
    row = conn.execute(
        f"SELECT id, username, email, role FROM users WHERE username = '{username}'"
    ).fetchone()
    return None if row is None else dict(zip(("id", "username", "email", "role"), row))
