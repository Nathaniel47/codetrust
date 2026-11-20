from urllib.parse import urlparse

from flask import Flask, redirect, request


def _is_local(target):
    parts = urlparse(target)
    return (
        target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
        and not parts.scheme
        and not parts.netloc
    )


def create_app():
    app = Flask(__name__)

    @app.get("/checkout/complete")
    def complete():
        target = request.args.get("return_url", "")
        return redirect(target if _is_local(target) else "/orders")

    return app
