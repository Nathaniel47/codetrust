import json


def dump_session(data):
    return json.dumps(data).encode()


def load_session(blob):
    return json.loads(blob)
