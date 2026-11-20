import os


def save_note(base_dir, title, text):
    base = os.path.realpath(base_dir)
    path = os.path.realpath(os.path.join(base, f"{title}.txt"))
    if os.path.commonpath([base, path]) != base:
        raise ValueError("invalid title")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
