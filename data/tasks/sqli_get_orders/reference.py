def get_orders(conn, user_id, status):
    rows = conn.execute(
        "SELECT id FROM orders WHERE user_id = ? AND status = ? ORDER BY id", (user_id, status)
    ).fetchall()
    return [r[0] for r in rows]
