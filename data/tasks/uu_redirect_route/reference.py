from urllib.parse import urlparse

from flask import Flask, redirect, request


def _allowed(url):
    if "\\" in url:
        return False
    parts = urlparse(url)
    if not parts.scheme and not parts.netloc:
        return url.startswith("/") and not url.startswith("//")
    return parts.scheme in ("http", "https") and parts.hostname == "docs.example.test"


def create_app():
    app = Flask(__name__)

    @app.get("/go")
    def go():
        url = request.args.get("url", "")
        if not _allowed(url):
            return "bad url", 400
        return redirect(url)

    return app
