import os

from flask import Flask, jsonify, request


def create_app(upload_dir):
    app = Flask(__name__)

    @app.post("/upload")
    def upload():
        f = request.files.get("file")
        if f is None or not f.filename:
            return jsonify(error="no file"), 400
        f.save(os.path.join(upload_dir, f.filename))
        return jsonify(filename=f.filename), 201

    return app
