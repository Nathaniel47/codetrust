import os


def get_db_config():
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "user": os.environ.get("DB_USER", "app"),
        "password": os.environ.get("DB_PASSWORD"),
        "name": os.environ.get("DB_NAME", "appdb"),
    }
