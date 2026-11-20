def get_orders(conn, user_id, status):
    rows = conn.execute(
        f"SELECT id FROM orders WHERE user_id = {user_id} AND status = '{status}' ORDER BY id"
    ).fetchall()
    return [r[0] for r in rows]
