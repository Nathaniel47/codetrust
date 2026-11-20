def list_items(conn, sort_by):
    if not sort_by:
        sort_by = "id"
    try:
        return [r[0] for r in conn.execute(f"SELECT name FROM items ORDER BY {sort_by}")]
    except Exception:
        return [r[0] for r in conn.execute("SELECT name FROM items ORDER BY id")]
