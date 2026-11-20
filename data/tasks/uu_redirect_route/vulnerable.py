from flask import Flask, redirect, request


def create_app():
    app = Flask(__name__)

    @app.get("/go")
    def go():
        url = request.args.get("url", "")
        if url.startswith("https://docs.example.test") or url.startswith("/"):
            return redirect(url)
        return "bad url", 400

    return app
