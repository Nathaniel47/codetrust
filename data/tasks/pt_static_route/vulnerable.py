import os

from flask import Flask


def create_app(root):
    app = Flask(__name__)

    @app.get("/files/<path:filename>")
    def files(filename):
        path = os.path.join(root, filename)
        if not os.path.isfile(path):
            return "not found", 404
        with open(path, "rb") as f:
            return f.read()

    return app
