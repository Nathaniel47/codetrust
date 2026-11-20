import subprocess


def recent_commits(repo_dir, author):
    out = subprocess.run(
        ["git", "log", f"--author={author}", "--oneline", "-n", "20"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout
    return out.splitlines()
