from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)
    invoices = [
        {"id": 1, "user_id": 1, "amount": 10},
        {"id": 2, "user_id": 2, "amount": 20},
        {"id": 3, "user_id": 1, "amount": 30},
    ]

    @app.get("/api/invoices")
    def list_invoices():
        uid = request.headers.get("X-User-Id")
        if not uid:
            return jsonify(error="unauthenticated"), 401
        wanted = request.args.get("user_id", uid)
        if wanted != uid and request.headers.get("X-Role") != "admin":
            return jsonify(error="forbidden"), 403
        return jsonify([i for i in invoices if str(i["user_id"]) == wanted])

    return app
