def is_allowed_image(filename):
    name = filename.lower()
    return any(f".{ext}" in name for ext in ("png", "jpg", "jpeg", "gif"))
