from flask import Flask, request
from markupsafe import escape


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return f"<h1>Hello, {escape(request.args.get('name', 'world'))}!</h1>"

    return app
