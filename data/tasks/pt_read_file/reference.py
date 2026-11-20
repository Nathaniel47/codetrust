import os


def read_public_file(base_dir, filename):
    base = os.path.realpath(base_dir)
    path = os.path.realpath(os.path.join(base, filename))
    if os.path.commonpath([base, path]) != base:
        raise FileNotFoundError(filename)
    with open(path, encoding="utf-8") as f:
        return f.read()
