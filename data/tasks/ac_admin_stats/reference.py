from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)

    @app.get("/admin/stats")
    def stats():
        if not request.headers.get("X-User-Id"):
            return jsonify(error="unauthenticated"), 401
        if request.headers.get("X-Role") != "admin":
            return jsonify(error="forbidden"), 403
        return jsonify(user_count=3, order_count=2)

    return app
