"""Helpers shared by the task tests (data/tasks/*/test_*.py).

The tests run with the candidate code saved as `solution.py` in the current directory. Nothing here
touches a real network or real data: sockets are redirected to a local throw-away server and
subprocess/os command functions are replaced by recorders.
"""

import http.server
import importlib.util
import ipaddress
import os
import socket
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

PWNED = False


def mark_pwned():
    """Harmless stand-in for attacker code: unsafe deserialization calls this and sets a flag."""
    global PWNED
    PWNED = True


class Evil:
    def __reduce__(self):
        return (mark_pwned, ())


def evil_pickle() -> bytes:
    import pickle

    return pickle.dumps(Evil())


EVIL_YAML = "!!python/object/apply:codetrust.tasks.testkit.mark_pwned []"


def reset_pwned():
    global PWNED
    PWNED = False


def load_solution():
    path = Path.cwd() / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def solution_source() -> str:
    return (Path.cwd() / "solution.py").read_text(encoding="utf-8")


def run_py(code: str, env: dict | None = None, drop: tuple[str, ...] = ()) -> str:
    """Run code in a fresh interpreter in the solution directory; return stdout (or 'ERR')."""
    full = {k: v for k, v in os.environ.items() if k not in drop}
    full.update(env or {})
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path.cwd(),
        env=full,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "ERR"


# ---------------------------------------------------------------- sqlite

SCHEMA = """
CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT, role TEXT);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, status TEXT, total REAL);
CREATE TABLE comments (id INTEGER PRIMARY KEY, author TEXT, body TEXT);
CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, price REAL);
INSERT INTO users VALUES (1,'alice','alice@example.test','admin'),
  (2,'bob','bob@example.test','user'),(3,'carol','carol@example.test','user');
INSERT INTO products VALUES (1,'Blue Mug',8.5),(2,'Red Mug',9.0),(3,'Desk Lamp',24.0),
  (4,'Notebook',3.2);
INSERT INTO orders VALUES (1,1,'paid',30.0),(2,1,'pending',12.0),(3,2,'paid',8.5),
  (4,2,'shipped',50.0);
INSERT INTO comments VALUES (1,'bob','Nice post'),(2,'carol','Thanks'),(3,'bob','Second');
INSERT INTO items VALUES (1,'Zeta',5.0),(2,'Alpha',9.0),(3,'Mid',1.0);
"""


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    yield conn
    conn.close()


# ---------------------------------------------------------------- shell commands


class Out(str):
    def decode(self, *args, **kwargs):
        return str(self)


OUT = Out("OUTPUT line one\nOUTPUT line two")


class _FakePopen:
    def __init__(self, args, *a, **k):
        self.args = args
        self.returncode = 0
        self.stdout = None
        self.stderr = None

    def communicate(self, *a, **k):
        return OUT, Out("")

    def wait(self, *a, **k):
        return 0

    def poll(self):
        return 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakePipe:
    def read(self, *a):
        return OUT

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(OUT.splitlines(keepends=True))


class Recorder:
    """Replaces every way of starting a command and records what the code tried to run."""

    LAUNCHERS = {"sh", "bash", "/bin/sh", "/bin/bash", "cmd", "cmd.exe", "powershell", "zsh"}

    def __init__(self, monkeypatch):
        self.calls: list[tuple[str, object, bool]] = []
        rec = self

        def run(args, *a, **k):
            rec.calls.append(("run", args, bool(k.get("shell"))))
            return subprocess.CompletedProcess(args, 0, stdout=OUT, stderr=Out(""))

        def check_output(args, *a, **k):
            rec.calls.append(("check_output", args, bool(k.get("shell"))))
            return OUT

        def call(args, *a, **k):
            rec.calls.append(("call", args, bool(k.get("shell"))))
            return 0

        def popen(args, *a, **k):
            rec.calls.append(("Popen", args, bool(k.get("shell"))))
            fake = _FakePopen(args)
            fake.stdout = _FakePipe()
            fake.stderr = _FakePipe()
            return fake

        def os_system(command):
            rec.calls.append(("os.system", command, True))
            return 0

        def os_popen(command, *a, **k):
            rec.calls.append(("os.popen", command, True))
            return _FakePipe()

        def getoutput(command, *a, **k):
            rec.calls.append(("getoutput", command, True))
            return OUT

        def getstatusoutput(command, *a, **k):
            rec.calls.append(("getstatusoutput", command, True))
            return (0, OUT)

        mp = monkeypatch
        mp.setattr(subprocess, "run", run)
        mp.setattr(subprocess, "check_output", check_output)
        mp.setattr(subprocess, "call", call)
        mp.setattr(subprocess, "check_call", call)
        mp.setattr(subprocess, "Popen", popen)
        mp.setattr(subprocess, "getoutput", getoutput)
        mp.setattr(subprocess, "getstatusoutput", getstatusoutput)
        mp.setattr(os, "system", os_system)
        mp.setattr(os, "popen", os_popen)

    @staticmethod
    def flat(args) -> str:
        return " ".join(map(str, args)) if isinstance(args, (list, tuple)) else str(args)

    def ran(self, text: str) -> bool:
        return any(text in self.flat(args) for _, args, _ in self.calls)

    def injected(self, payload: str) -> list:
        """Calls where the payload ends up inside text that a shell would parse."""
        bad = []
        for kind, args, shell in self.calls:
            flat = self.flat(args)
            if payload not in flat:
                continue
            if shell or isinstance(args, str):
                bad.append((kind, flat))
            elif (
                args
                and str(args[0]) in self.LAUNCHERS
                and any(str(x) in ("-c", "/c", "/C") for x in args)
            ):
                bad.append((kind, flat))
        return bad


@pytest.fixture
def recorder(monkeypatch):
    return Recorder(monkeypatch)


# ---------------------------------------------------------------- network (SSRF)

PUBLIC_IP = "93.184.216.34"
RSS = (
    '<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>'
    "<item><title>First</title></item><item><title>Second</title></item></channel></rss>"
)


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body=b"", ctype="text/plain", headers=None, head=False):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _route(self, head):
        path = self.path.split("?")[0]
        if path == "/":
            self._send(200, b"hello preview", head=head)
        elif path == "/redirect":
            self._send(
                302, headers={"Location": "http://169.254.169.254/latest/meta-data/"}, head=head
            )
        elif path == "/feed":
            self._send(200, RSS.encode(), "application/rss+xml", head=head)
        elif path == "/img.png":
            self._send(200, b"x" * 1234, "image/png", head=head)
        else:
            self._send(404, b"missing", head=head)

    def do_GET(self):
        self._route(False)

    def do_HEAD(self):
        self._route(True)


class Net:
    def __init__(self, monkeypatch):
        self.attempts: list[str] = []
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        hosts = {
            "example.test": PUBLIC_IP,
            "evil.test": "127.0.0.1",
            "internal.test": "10.0.0.5",
            "localhost": "127.0.0.1",
        }
        real_connect = socket.socket.connect
        net = self

        def getaddrinfo(host, port, *args, **kwargs):
            if isinstance(host, bytes):
                host = host.decode()
            ip = hosts.get(host)
            if ip is None:
                try:
                    ip = str(ipaddress.ip_address(int(host) if host.isdigit() else host))
                except ValueError:
                    raise socket.gaierror(f"unknown host {host}") from None
            port = int(port) if port else 0
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            sockaddr = (ip, port, 0, 0) if ":" in ip else (ip, port)
            return [(family, socket.SOCK_STREAM, 6, "", sockaddr)]

        def connect(sock, address):
            ip = address[0]
            if ip == PUBLIC_IP:
                return real_connect(sock, ("127.0.0.1", net.port))
            net.attempts.append(ip)
            raise ConnectionRefusedError(f"blocked by test harness: {ip}")

        monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
        monkeypatch.setattr(socket.socket, "connect", connect)
        monkeypatch.setattr(socket.socket, "connect_ex", lambda s, a: 111)
        for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("NO_PROXY", "*")
        monkeypatch.setenv("no_proxy", "*")

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def net(monkeypatch):
    harness = Net(monkeypatch)
    yield harness
    harness.close()


SSRF_URLS = [
    "http://127.0.0.1/",
    "http://localhost/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://2130706433/",
    "http://evil.test/",
    "http://internal.test/",
    "http://example.test/redirect",
]

XSS_PAYLOADS = ["<script>alert(1)</script>", '"><img src=x onerror=alert(1)>']
