import requests


def fetch_url_preview(url):
    return requests.get(url, timeout=5).text[:200]
