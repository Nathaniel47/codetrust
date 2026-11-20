def is_allowed_image(filename):
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in {"png", "jpg", "jpeg", "gif"}
