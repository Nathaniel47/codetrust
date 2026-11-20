import html


def render_profile_card(user):
    name, bio, site = (html.escape(user[k]) for k in ("name", "bio", "website"))
    return f'<div class="card"><h2>{name}</h2><p>{bio}</p><a href="{site}">Website</a></div>'
