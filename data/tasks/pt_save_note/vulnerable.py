import os


def save_note(base_dir, title, text):
    path = os.path.join(base_dir, f"{title}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
