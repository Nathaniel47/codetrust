from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)
    orders = {
        1: {"id": 1, "owner_id": 1, "item": "Desk Lamp"},
        2: {"id": 2, "owner_id": 2, "item": "Notebook"},
    }

    @app.get("/api/orders/<int:order_id>")
    def get_order(order_id):
        if not request.headers.get("X-User-Id"):
            return jsonify(error="unauthenticated"), 401
        order = orders.get(order_id)
        if order is None:
            return jsonify(error="not found"), 404
        return jsonify(order)

    return app
