import pickle


def save_cache_entry(path, obj):
    with open(path, "wb") as f:
        pickle.dump(obj, f)


def load_cache_entry(path):
    with open(path, "rb") as f:
        return pickle.load(f)
