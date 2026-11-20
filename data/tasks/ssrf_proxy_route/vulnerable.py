import requests
from flask import Flask, request


def create_app():
    app = Flask(__name__)

    @app.get("/fetch")
    def fetch():
        return requests.get(request.args.get("url", ""), timeout=5).text

    return app
