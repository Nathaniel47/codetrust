import pickle


def dump_session(data):
    return pickle.dumps(data)


def load_session(blob):
    return pickle.loads(blob)
