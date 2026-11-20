def list_items(conn, sort_by):
    column = sort_by if sort_by in ("name", "price") else "id"
    return [r[0] for r in conn.execute(f"SELECT name FROM items ORDER BY {column}")]
