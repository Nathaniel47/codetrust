import os


def list_directory(base_dir, subpath):
    base = os.path.realpath(base_dir)
    target = os.path.realpath(os.path.join(base, subpath))
    if os.path.commonpath([base, target]) != base:
        raise ValueError("outside base directory")
    return sorted(os.listdir(target))
