def delete_comment(conn, comment_id, author):
    cur = conn.execute("DELETE FROM comments WHERE id = ? AND author = ?", (comment_id, author))
    conn.commit()
    return cur.rowcount
