import os
import subprocess

from codetrust.tasks.testkit import Recorder


def test_recorder_flags_shell_use_but_not_list_form(monkeypatch):
    rec = Recorder(monkeypatch)
    subprocess.run(["ping", "-c", "1", "a; echo pwned"])
    assert rec.injected("a; echo pwned") == []
    os.system("ping a; echo pwned")
    subprocess.run("ping a; echo pwned", shell=True)
    subprocess.run(["sh", "-c", "ping a; echo pwned"])
    assert len(rec.injected("a; echo pwned")) == 3
    assert rec.ran("ping")


def test_fake_output_behaves_like_text_and_bytes(monkeypatch):
    Recorder(monkeypatch)
    out = subprocess.check_output(["x"])
    assert "OUTPUT" in out and out.decode().splitlines()[0].startswith("OUTPUT")
