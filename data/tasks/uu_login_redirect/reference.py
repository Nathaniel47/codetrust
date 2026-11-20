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

    @app.post("/login")
    def login():
        if request.form.get("username") != "alice" or request.form.get("password") != "s3cret":
            return "invalid credentials", 401
        target = request.args.get("next", "")
        return redirect(target if _is_local(target) else "/dashboard")

    return app
