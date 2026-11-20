import os


def convert_image(src, dst):
    return os.system(f"convert {src} {dst}") == 0
