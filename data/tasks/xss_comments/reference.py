import html


def render_comments(comments):
    items = "".join(
        f"<li><strong>{html.escape(c['author'])}</strong>: {html.escape(c['text'])}</li>"
        for c in comments
    )
    return f"<ul>{items}</ul>"
