from database import db
from src import utils
from database.users import correct_best_wpm
import database.modified_races as modified_races


def add_races(username, races):
    batch_size = 50
    for i in range(0, len(races), batch_size):
        batch = races[i:i + batch_size]
        query = "INSERT OR IGNORE INTO races VALUES"
        params = []
        for race in batch:
            query += "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?),"
            race_id = f"{username}|{race['gn']}"
            params += [
                race_id, username, race['tid'], race['gn'], race['wpm'],
                race['ac'], race['pts'], race['r'], race['np'], race['t']
            ]
        query = query[:-1]
        db.run(query, params)


def get_races(username, start_time=None, end_time=None, start_number=None, end_number=None,
              with_texts=False, order_by=None, reverse=False, limit=None, columns="*"):
    if columns != "*":
        columns = ",".join([c for c in columns])
    order = 'DESC' if reverse else 'ASC'

    races = db.fetch(
        f"""
            SELECT {columns} FROM races
            {'JOIN texts ON texts.id = races.text_id' * with_texts}
            WHERE username = ?
            {f'AND number >= {start_number}' if start_number else ''}
            {f'AND number <= {end_number}' if end_number else ''}
            {f'AND timestamp >= {start_time}' if start_time else ''}
            {f'AND timestamp < {end_time}' if end_time else ''}
            {f'ORDER BY {order_by} {order}' if order_by else ''}
            {f'LIMIT {limit}' if limit else ''}
        """,
        [username],
    )

    return races


def get_race(username, number):
    race = db.fetch(
        """
            SELECT * FROM races
            WHERE username = ?
            AND number = ?
        """,
        [username, number]
    )

    if not race:
        return None

    return race[0]


def get_text_races(username, text_id):
    races = db.fetch(
        """
            SELECT * FROM races
            WHERE username = ?
            AND text_id = ?
            ORDER BY timestamp ASC
        """,
        [username, text_id],
    )

    return races

async def correct_race(username, race_number, race):
    print(f"Correcting WPM for race {username}|{race_number}")

    import database.text_results as top_tens
    id = f"{username}|{race_number}"
    wpm = race["lagged"]
    unlagged_wpm = race["unlagged"]
    points = utils.calculate_points(race["quote"], unlagged_wpm)

    # Updating WPM & points in the main table
    print("Updating races table")
    db.run("""
        UPDATE races
        SET wpm = ?, points = ?
        WHERE id = ?
    """, [round(unlagged_wpm, 2), points, id])

    # Adding race to modified races
    print("Updating modified_races table")
    modified_races.add_race(username, race_number, wpm, unlagged_wpm)

    # Removing the race from text results
    print("Deleting from top 10 results")
    id = f"{username}|{race_number}"
    top_tens.delete_result(id)
    text_id = db.fetch("""
        SELECT text_id
        FROM races
        WHERE id = ?
    """, [id])[0][0]

    # Updating top 10
    print("Updating top ten")
    await top_tens.update_results(text_id)

    # Correcting user's best WPM in the users table
    print("Correcting best wpm")
    correct_best_wpm(username)

def delete_race(username, race_number):
    print(f"!!! DELETING RACE {username}|{race_number}")

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