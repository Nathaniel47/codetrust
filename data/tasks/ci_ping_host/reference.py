import subprocess


def ping_host(host):
    result = subprocess.run(
        ["ping", "-c", "1", host], capture_output=True, text=True, timeout=10
    )
    return result.stdout
