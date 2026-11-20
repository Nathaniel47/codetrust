import os
import secrets

from flask import Flask


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("APP_SECRET_KEY") or secrets.token_hex(32)
    return app
