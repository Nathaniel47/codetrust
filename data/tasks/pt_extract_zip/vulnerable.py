import os
import zipfile


def extract_archive(zip_path, dest_dir):
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            target = os.path.join(dest_dir, info.filename)
            if info.is_dir():
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                out.write(src.read())
            count += 1
    return count
