from flask import Flask, redirect, request


def create_app():
    app = Flask(__name__)

    @app.get("/checkout/complete")
    def complete():
        return redirect(request.args.get("return_url", "/orders"))

    return app
