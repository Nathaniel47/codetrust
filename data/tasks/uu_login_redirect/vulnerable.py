from flask import Flask, redirect, request


def create_app():
    app = Flask(__name__)

    @app.post("/login")
    def login():
        if request.form.get("username") != "alice" or request.form.get("password") != "s3cret":
            return "invalid credentials", 401
        return redirect(request.args.get("next", "/dashboard"))

    return app
