import subprocess


def convert_image(src, dst):
    return subprocess.run(["convert", src, dst], timeout=30).returncode == 0
