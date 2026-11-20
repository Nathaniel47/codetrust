def delete_comment(conn, comment_id, author):
    cur = conn.execute(
        f"DELETE FROM comments WHERE id = {comment_id} AND author = '{author}'"
    )
    conn.commit()
    return cur.rowcount
