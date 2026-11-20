import os

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename

ALLOWED = {"png", "jpg", "jpeg", "gif"}


def create_app(upload_dir):
    app = Flask(__name__)

    @app.post("/upload")
    def upload():
        f = request.files.get("file")
        if f is None or not f.filename:
            return jsonify(error="no file"), 400
        name = secure_filename(f.filename)
        if "." not in name or name.rsplit(".", 1)[1].lower() not in ALLOWED:
            return jsonify(error="unsupported type"), 400
        f.save(os.path.join(upload_dir, name))
        return jsonify(filename=name), 201

    return app
