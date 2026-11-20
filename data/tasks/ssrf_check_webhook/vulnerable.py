import requests


def webhook_is_reachable(url):
    try:
        return requests.get(url, timeout=5).status_code < 400
    except Exception:
        return False
