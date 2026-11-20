import json


def save_cache_entry(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def load_cache_entry(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
