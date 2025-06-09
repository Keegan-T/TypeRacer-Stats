from database.bot import db


def get_recent(channel_id):
    text_id = db.fetch("""
        SELECT text_id
        FROM recent_text_ids
        WHERE channel_id = ?
    """, [channel_id])

    if not text_id:
        return None

    return text_id[0][0]


def update_recent(channel_id, text_id):
    db.run("""
        INSERT INTO recent_text_ids (channel_id, text_id)
        VALUES (?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET text_id = excluded.text_id;
    """, [channel_id, text_id])
