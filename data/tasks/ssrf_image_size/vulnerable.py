import requests


def remote_image_size(url):
    return len(requests.get(url, timeout=5).content)
