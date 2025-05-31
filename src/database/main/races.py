import database.main.modified_races as modified_races
from database.main import db
from database.main.users import correct_best_wpm
from utils.logging import log
from utils.stats import calculate_points


def add_races(races):
    db.run_many(f"""
        INSERT OR IGNORE INTO races
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, races)


async def get_races(username, columns="*", start_date=None, end_date=None, start_number=None, end_number=None,
                    order_by=None, reverse=False, limit=None, universe="play"):
    if columns != "*":
        columns = ",".join([c for c in columns])
    order = 'DESC' if reverse else 'ASC'

    batch_size = 100_000
    offset = 0

    if limit:
        limit_string = f"LIMIT {limit}"
    else:
        limit_string = f"LIMIT {batch_size} OFFSET {offset}"

    race_list = []
    while True:
        batch_races = await db.fetch_async(f"""
            SELECT {columns} FROM RACES
            INDEXED BY idx_races_universe_username
            WHERE universe = ?
            AND username = ?
            {f'AND number >= {start_number}' if start_number else ''}
            {f'AND number <= {end_number}' if end_number else ''}
            {f'AND timestamp >= {start_date}' if start_date else ''}
            {f'AND timestamp < {end_date}' if end_date else ''}
            {f'ORDER BY {order_by} {order}' if order_by else ''}
            {limit_string}
        """, [universe, username])

        race_list += batch_races

        if limit or not batch_races:
            break

        offset += batch_size
        limit_string = f"LIMIT {batch_size} OFFSET {offset}"

    return race_list


def get_race(username, number, universe):
    race = db.fetch(f"""
        SELECT * FROM races
        WHERE universe = ?
        AND username = ?
        AND number = ?
    """, [universe, username, number])

    if not race:
        return None

    return race[0]


def get_text_races(username, text_id, universe, start_date=None, end_date=None):
    races = db.fetch(f"""
        SELECT * FROM races
        INDEXED BY idx_races_universe_username_text_id
        WHERE universe = ?
        AND username = ?
        AND text_id = ?
        {f'AND timestamp >= {start_date}' if start_date else ''}
        {f'AND timestamp < {end_date}' if end_date else ''}
        ORDER BY timestamp ASC
    """, [universe, username, text_id])

    return races


async def correct_race(universe, username, race_number, race):
    log(f"Correcting WPM for race {universe}|{username}|{race_number}")

    import database.main.text_results as top_tens
    wpm = race["lagged"]
    unlagged_wpm = race["unlagged"]
    points = calculate_points(race["quote"], unlagged_wpm)

    # Updating WPM & points in the main table
    db.run("""
        UPDATE races
        SET wpm = ?, points = ?
        WHERE universe = ?
        AND username = ?
        AND number = ?
    """, [round(unlagged_wpm, 2), points, universe, username, race_number])

    # Adding race to modified races
    modified_races.add_race(universe, username, race_number, wpm, unlagged_wpm)

    # Removing the race from text results
    top_tens.delete_result(username, race_number)

    # Updating top 10
    await top_tens.update_results(race["text_id"])

    # Correcting user's best WPM in the users table
    correct_best_wpm(username, universe)


async def delete_race(username, race_number, universe="play"):
    log(f"Deleting race {universe}|{username}|{race_number}")

    db.run("""
        INSERT OR IGNORE INTO deleted_races (universe, username, number, wpm_registered)
        SELECT universe, username, number, wpm FROM races
        WHERE universe = ?
        AND username = ?
        AND number = ?
    """, [universe, username, race_number])

    db.run("""
        DELETE FROM races
        WHERE universe = ?
        AND username = ?
        AND number = ?
    """, [universe, username, race_number])

    if universe == "play":
        db.run("""
            DELETE FROM text_results
            WHERE username = ?
            AND number = ?
        """, [username, race_number])

    correct_best_wpm(username, universe)
