from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)
    users = {1: "alice", 2: "bob", 3: "carol"}

    @app.delete("/api/users/<int:user_id>")
    def delete_user(user_id):
        if not request.headers.get("X-User-Id"):
            return jsonify(error="unauthenticated"), 401
        if request.headers.get("X-Role") != "admin":
            return jsonify(error="forbidden"), 403
        if users.pop(user_id, None) is None:
            return jsonify(error="not found"), 404
        return "", 204

    return app
