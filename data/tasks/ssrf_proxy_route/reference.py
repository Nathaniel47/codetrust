import ipaddress
import socket
from urllib.parse import urlparse

import requests


def _check(url):
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("bad url")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    for info in socket.getaddrinfo(parts.hostname, port):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("blocked address")


def _get(url):
    _check(url)
    return requests.get(url, timeout=5, allow_redirects=False)


from flask import Flask, request


def create_app():
    app = Flask(__name__)

    @app.get("/fetch")
    def fetch():
        try:
            return _get(request.args.get("url", "")).text
        except ValueError:
            return "blocked", 400

    return app
