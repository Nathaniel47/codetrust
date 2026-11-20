import pickle


def encode_job(name, args):
    return pickle.dumps((name, args))


def decode_job(message):
    return pickle.loads(message)
