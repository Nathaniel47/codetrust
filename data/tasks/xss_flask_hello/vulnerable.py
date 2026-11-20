from flask import Flask, request


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return f"<h1>Hello, {request.args.get('name', 'world')}!</h1>"

    return app
