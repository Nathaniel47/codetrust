from flask import Flask, send_from_directory


def create_app(root):
    app = Flask(__name__)

    @app.get("/files/<path:filename>")
    def files(filename):
        return send_from_directory(root, filename)

    return app
