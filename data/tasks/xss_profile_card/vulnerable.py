def render_profile_card(user):
    return (
        f'<div class="card"><h2>{user["name"]}</h2><p>{user["bio"]}</p>'
        f'<a href="{user["website"]}">Website</a></div>'
    )
