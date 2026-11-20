from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)
    profiles = {1: {"id": 1, "bio": "hi"}, 2: {"id": 2, "bio": "hello"}}

    @app.put("/api/profile/<int:user_id>")
    def update_profile(user_id):
        uid = request.headers.get("X-User-Id")
        if not uid:
            return jsonify(error="unauthenticated"), 401
        if user_id not in profiles:
            return jsonify(error="not found"), 404
        if str(user_id) != uid and request.headers.get("X-Role") != "admin":
            return jsonify(error="forbidden"), 403
        profiles[user_id]["bio"] = (request.get_json(silent=True) or {}).get("bio", "")
        return jsonify(profiles[user_id])

    return app
