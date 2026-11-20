import subprocess


def gzip_file(path):
    subprocess.run(["gzip", "-k", path], check=True, timeout=60)
    return path + ".gz"
