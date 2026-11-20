import subprocess


def gzip_file(path):
    subprocess.run(f"gzip -k {path}", shell=True, check=True)
    return path + ".gz"
