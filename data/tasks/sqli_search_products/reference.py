def search_products(conn, term):
    rows = conn.execute(
        "SELECT name FROM products WHERE name LIKE ? ORDER BY name", (f"%{term}%",)
    ).fetchall()
    return [r[0] for r in rows]
