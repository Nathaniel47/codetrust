def render_search_page(query, results):
    items = "".join(f"<li>{r}</li>" for r in results)
    return f'<h1>Results for "{query}"</h1><ul>{items}</ul>'
