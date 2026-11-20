import os

from flask import Flask


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-secret-key")
    return app
