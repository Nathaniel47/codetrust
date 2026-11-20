def search_products(conn, term):
    rows = conn.execute(
        f"SELECT name FROM products WHERE name LIKE '%{term}%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]
