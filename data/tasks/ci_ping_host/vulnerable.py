import os


def ping_host(host):
    return os.popen(f"ping -c 1 {host}").read()
