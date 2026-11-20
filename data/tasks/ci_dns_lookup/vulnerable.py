import subprocess


def lookup_host(domain):
    return subprocess.getoutput(f"nslookup {domain}")
