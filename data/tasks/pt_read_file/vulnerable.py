import os


def read_public_file(base_dir, filename):
    with open(os.path.join(base_dir, filename), encoding="utf-8") as f:
        return f.read()
