import os


def list_directory(base_dir, subpath):
    return sorted(os.listdir(os.path.join(base_dir, subpath)))
