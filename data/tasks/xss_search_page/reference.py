import html


def render_search_page(query, results):
    items = "".join(f"<li>{html.escape(r)}</li>" for r in results)
    return f'<h1>Results for "{html.escape(query)}"</h1><ul>{items}</ul>'
