import subprocess


def recent_commits(repo_dir, author):
    out = subprocess.check_output(
        f'git log --author="{author}" --oneline -n 20', shell=True, cwd=repo_dir, text=True
    )
    return out.splitlines()
