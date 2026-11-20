def render_comments(comments):
    items = "".join(f"<li><strong>{c['author']}</strong>: {c['text']}</li>" for c in comments)
    return f"<ul>{items}</ul>"
