import database.modified_races as modified_races
from database import db
from database.users import correct_best_wpm
from utils import strings
from utils.stats import calculate_points
from utils.logging import send_message

def table_name(universe):
    table = "races"
    if universe != "play":
        table += f"_{universe}"

    return table.replace("-", "_")


def create_table(universe):
    table = table_name(universe)
    db.run(f"""
        CREATE TABLE {table} (
            id TEXT PRIMARY KEY,
            username TEXT,
            text_id INTEGER,
            number INTEGER,
            wpm REAL,
            accuracy REAL,
            points REAL,
            rank INTEGER,
            racers INTEGER,
            timestamp REAL
        )
    """)

    db.run(f"CREATE INDEX idx_{table}_username ON {table}(username)")
    db.run(f"CREATE INDEX idx_{table}_text_id ON {table}(text_id)")
    db.run(f"CREATE INDEX idx_{table}_username_text_id ON {table}(username, text_id)")
    db.run(f"CREATE INDEX idx_{table}_username_text_id_wpm ON {table}(username, text_id, wpm)")


def add_races(races, universe):
    table = table_name(universe)
    db.run_many(f"""
        INSERT OR IGNORE INTO {table}
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, races)


async def get_races(username, columns="*", start_time=None, end_time=None, start_number=None, end_number=None,
                    with_texts=False, order_by=None, reverse=False, limit=None, universe="play"):
    from database.texts import table_name as texts_table_name
    table = table_name(universe)
    texts_table = texts_table_name(universe)
    if columns != "*":
        columns = ",".join([c for c in columns])
    order = 'DESC' if reverse else 'ASC'

    races = await db.fetch_async(f"""
        SELECT {columns} FROM {table}
        INDEXED BY idx_{table}_username
        {('JOIN ' + texts_table + ' ON ' + texts_table + '.id = ' + table + '.text_id') * with_texts}
        WHERE username = ?
        {f'AND number >= {start_number}' if start_number else ''}
        {f'AND number <= {end_number}' if end_number else ''}
        {f'AND timestamp >= {start_time}' if start_time else ''}
        {f'AND timestamp < {end_time}' if end_time else ''}
        {f'ORDER BY {order_by} {order}' if order_by else ''}
        {f'LIMIT {limit}' if limit else ''}
    """, [username])

    return races


def get_race(username, number, universe):
    table = table_name(universe)
    race = db.fetch(f"""
        SELECT * FROM {table}
        WHERE id = ?
    """, [strings.race_id(username, number)])

    if not race:
        return None

    return race[0]


def get_text_races(username, text_id, universe):
    table = table_name(universe)
    races = db.fetch(f"""
        SELECT * FROM {table}
        INDEXED BY idx_{table}_username_text_id
        WHERE username = ?
        AND text_id = ?
        ORDER BY timestamp ASC
    """, [username, text_id])

    return races


async def correct_race(username, race_number, race):
    await send_message(f"Correcting WPM for race {username}|{race_number}")

    import database.text_results as top_tens
    id = f"{username}|{race_number}"
    wpm = race["lagged"]
    unlagged_wpm = race["unlagged"]
    points = calculate_points(race["quote"], unlagged_wpm)

    # Updating WPM & points in the main table
    db.run("""
        UPDATE races
        SET wpm = ?, points = ?
        WHERE id = ?
    """, [round(unlagged_wpm, 2), points, id])

    # Adding race to modified races
    modified_races.add_race(username, race_number, wpm, unlagged_wpm)

    # Removing the race from text results
    id = f"{username}|{race_number}"
    top_tens.delete_result(id)
    text_id = db.fetch("""
        SELECT text_id
        FROM races
        WHERE id = ?
    """, [id])[0][0]

    # Updating top 10
    await top_tens.update_results(text_id)

    # Correcting user's best WPM in the users table
    correct_best_wpm(username)


async def delete_race(username, race_number):
    await send_message(f"Deleting race {username}|{race_number}")

    db.run("""
        INSERT INTO modified_races (id, username, number, wpm)
        SELECT id, username, number, wpm FROM races
        WHERE username = ?
        AND number = ?
    """, [username, race_number])

    db.run("""
        DELETE FROM races
        WHERE username = ?
        AND number = ?
    """, [username, race_number])

    correct_best_wpm(username)


def delete_races_after_timestamp(username, timestamp):
    db.run("""
        DELETE FROM races
        WHERE username = ?
        AND timestamp >= ?
    """, [username, timestamp])
