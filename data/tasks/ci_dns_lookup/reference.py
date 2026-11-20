import subprocess


def lookup_host(domain):
    return subprocess.run(["nslookup", domain], capture_output=True, text=True, timeout=10).stdout
