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


def test_programs_appear_installed_and_full_path_shells_are_still_caught(monkeypatch):
    import shutil

    rec = Recorder(monkeypatch)
    assert shutil.which("convert") == "/usr/bin/convert"
    subprocess.run([shutil.which("convert"), "a; echo pwned"])
    assert rec.ran("convert") and rec.injected("a; echo pwned") == []
    subprocess.run([shutil.which("sh"), "-c", "convert a; echo pwned"])
    assert len(rec.injected("a; echo pwned")) == 1
