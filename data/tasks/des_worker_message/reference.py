import json


def encode_job(name, args):
    return json.dumps({"name": name, "args": args}).encode()


def decode_job(message):
    data = json.loads(message)
    return data["name"], data["args"]
