import database.main.db as db


def get_records(category):
    record_list = db.fetch("""
        SELECT name, username, record, date,link
        FROM records
        WHERE category = ?
    """, [category])

    return record_list


def update_record(category, index, username, record, date, link):
    name = db.fetch("SELECT name FROM records WHERE category = ? AND idx = ?", [category, index])
    db.run("""
        UPDATE records
        SET username = ?, record = ?, date = ?, link = ?
        WHERE category = ? AND idx = ?
    """, [username, record, date, link, category, index])

    return name[0][0]
