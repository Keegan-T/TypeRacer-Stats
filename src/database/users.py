import time

from database import db, texts
from database.texts import filter_disabled_texts, get_disabled_text_ids
from utils import strings
from utils.logging import log
from utils.stats import get_text_stats, calculate_text_bests
from utils.strings import get_date_query_string


def table_name(universe):
    table = "users"
    if universe != "play":
        table += f"_{universe}"

    return table.replace("-", "_")


def races_table_name(universe):
    table = "races"
    if universe != "play":
        table += f"_{universe}"

    return table.replace("-", "_")


def create_table(universe):
    table = table_name(universe)
    db.run(f"""
        CREATE TABLE {table} (
            username TEXT,
            display_name TEXT,
            premium INT,
            has_pic INT,
            country TEXT,
            joined INT,
            wpm_average_all_time REAL,
            wpm_average_last_10 REAL,
            wpm_best REAL,
            wpm_verified REAL,
            races INT,
            wins INT,
            points REAL,
            points_retroactive REAL,
            seconds REAL,
            characters INT,
            awards_first INT,
            awards_second INT,
            awards_third INT,
            texts_typed INT,
            text_best_average REAL,
            text_wpm_total REAL,
            avatar TEXT,
            disqualified INT,
            last_updated REAL
        )
    """)

    db.run(f"CREATE UNIQUE INDEX idx_{table}_username ON {table} (username)")


def add_user(username, universe):
    table = table_name(universe)
    db.run(f"""
        INSERT INTO {table} (username)
        VALUES (?)
    """, [username])


def get_users():
    users = db.fetch("SELECT * FROM users")

    return users


def get_user(username, universe="play"):
    table = table_name(universe)
    user = db.fetch(
        f"SELECT * FROM {table} WHERE username = ?",
        [username]
    )
    if not user:
        return None
    elif user[0]["races"] == 0 or not user[0]["last_updated"]:
        return None
    return user[0]


async def time_travel_stats(stats, user):
    from database.races import get_races
    stats = dict(stats)
    username = stats["username"]
    universe = user["universe"]
    start_date = user["start_date"]
    end_date = user["end_date"]
    columns = ["*"]
    race_list = await get_races(username, columns, start_date, end_date, universe=universe)
    text_bests = calculate_text_bests(race_list)

    if not race_list:
        races = 0
    else:
        numbers = [race["number"] for race in race_list]
        races = max(numbers) - min(numbers) + 1
    points = 0
    wins = 0
    total_wpm = 0
    best_wpm = 0
    for race in race_list:
        points += race["points"]
        wins += 1 if (race["rank"] == 1 and race["racers"] > 1) else 0
        total_wpm += race["wpm"]
        best_wpm = max(race["wpm"], best_wpm)

    try:
        average_wpm = total_wpm / len(race_list)
    except ZeroDivisionError:
        average_wpm = 0

    stats["races"] = races
    stats["points"] = points
    stats["wins"] = wins
    stats["wpm_average"] = average_wpm
    stats["wpm_best"] = best_wpm
    stats["text_wpm_total"] = sum([text["wpm"] for text in text_bests])
    stats["texts_typed"] = len(text_bests)
    if not text_bests:
        stats["text_best_average"] = 0
    else:
        stats["text_best_average"] = stats["text_wpm_total"] / stats["texts_typed"]

    return stats


def get_most(column, limit):
    top = db.fetch(f"""
        SELECT * FROM users
        WHERE disqualified = 0
        ORDER BY {column} DESC
        LIMIT ?
    """, [limit])

    return top


def get_most_texts_typed(limit):
    leaders = get_most("texts_typed", limit)
    text_count = texts.get_text_count()
    results = []

    for user in leaders:
        min_repeats = 1
        if user["texts_typed"] == text_count:
            username = user["username"]
            repeats = db.fetch("""
                SELECT r.text_id, COUNT(*) as times_typed
                FROM races r
                JOIN texts t ON r.text_id = t.id
                WHERE r.username = ?
                AND t.disabled = 0
                GROUP BY r.text_id;
            """, [username])

            min_repeats = min([row[1] for row in repeats])
        results.append((user, user["texts_typed"], min_repeats))

    results.sort(key=lambda x: (x[2], x[1]), reverse=True)

    return results


async def get_most_text_repeats(limit):
    top = await db.fetch_async("""
        SELECT username, text_id, MAX(times_typed) AS max_times
        FROM (
            SELECT username, text_id, COUNT(*) AS times_typed
            FROM races
            INDEXED BY idx_races_username_text_id
            GROUP BY username, text_id
        ) AS subquery
        GROUP BY username
        ORDER BY max_times DESC
        LIMIT ?;
    """, [limit])

    top_dict = {}

    for user in top:
        username, max_quote, max_quote_times = user
        top_dict[username] = {
            "max_quote_id": max_quote,
            "max_quote_times": max_quote_times,
        }

    username_list = ",".join([f"'{user[0]}'" for user in top])
    user_list = db.fetch(f"""
        SELECT * FROM users
        WHERE username IN ({username_list})
    """)
    user_list = [dict(user) for user in user_list]
    for user in user_list:
        username = user["username"]
        user["max_quote_id"] = top_dict[username]["max_quote_id"]
        user["max_quote_times"] = top_dict[username]["max_quote_times"]

    user_list.sort(key=lambda x: x["max_quote_times"], reverse=True)

    return user_list


def get_most_daily_races(limit):
    top = db.fetch(
        """
            SELECT *,
                CAST (races AS REAL) / (CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1)
                AS daily_races,
                CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1 AS days
            FROM users
            WHERE CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1 >= 90
            ORDER BY daily_races DESC
            LIMIT ?
        """,
        [limit]
    )

    return top


def get_most_daily_points(limit):
    top = db.fetch(
        """
            SELECT *,
                (points + points_retroactive) AS points_total,
                (points + points_retroactive) / (CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1)
                AS daily_points,
                CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1 AS days
            FROM users
            WHERE CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1 >= 90
            ORDER BY daily_points DESC
            LIMIT ?
        """,
        [limit]
    )

    return top


def get_most_total_points(limit):
    top = db.fetch(
        """
            SELECT *, (points + points_retroactive) AS points_total    
            FROM users ORDER BY points_total DESC
            LIMIT ?
        """,
        [limit]
    )

    return top


def get_top_text_best(limit):
    from database.texts import get_text_count
    text_count = get_text_count()
    min_texts = int(text_count * 0.2)
    top = db.fetch("""
        SELECT * FROM users
        WHERE texts_typed >= ?
        AND disqualified = 0
        ORDER BY text_best_average DESC
        LIMIT ?
    """, [min_texts, limit])

    return top


def get_most_awards(limit):
    top = db.fetch(
        """
            SELECT *, (awards_first + awards_second + awards_third) as awards_total FROM users
            ORDER BY awards_total DESC
            LIMIT ?
        """,
        [limit]
    )

    return top


async def get_most_texts_over(wpm):
    top = await db.fetch_async("""
        SELECT r.*, u.*, COUNT(DISTINCT r.text_id) AS unique_texts
        FROM races r
        JOIN users u ON r.username = u.username
        WHERE r.wpm > ? AND u.disqualified = 0
        GROUP BY r.username
        ORDER BY unique_texts DESC
        LIMIT 10;
    """, [wpm])

    return top


def update_stats(user, universe):
    table = table_name(universe)
    db.run(f"""
        UPDATE {table}
        SET username = ?, display_name = ?, premium = ?, has_pic = ?, country = ?, joined = ?,
        wpm_average_all_time = ?, wpm_average_last_10 = ?, wpm_best = ?, wpm_verified = ?,
        races = ?, wins = ?, points = ?, points_retroactive = ?, seconds = ?, characters = ?, 
        avatar = ?, disqualified = ?, last_updated = ?
        WHERE username = ?
    """, (
        user['username'], user['display_name'], user['premium'], user['has_pic'], user['country'],
        user['joined'], user['wpm_average'], user['wpm_last_10'], user['wpm_best'], user['wpm_verified'],
        user['races'], user['wins'], user['points'], user['retroactive_points'], user['seconds'],
        user['characters'], user['avatar'], user['disqualified'], time.time(),
        user['username']
    ))


def update_text_stats(username, universe):
    table = table_name(universe)
    text_bests = get_text_bests(username, universe=universe)
    stats = get_text_stats(text_bests)

    db.run(f"""
        UPDATE {table}
        SET texts_typed = ?, text_best_average = ?, text_wpm_total = ?
        WHERE username = ? 
    """, [
        stats['texts_typed'], stats['text_best_average'],
        stats['text_wpm_total'], username
    ])


def update_awards(username, first, second, third):
    db.run("""
        UPDATE users
        SET awards_first = ?, awards_second = ?, awards_third = ?
        WHERE username = ?
    """, [first, second, third, username])


async def delete_user(username):
    log(f"Deleting user {username}")
    db.run(
        "DELETE FROM races WHERE username = ?",
        [username]
    )
    db.run(
        "DELETE FROM users WHERE username = ?",
        [username]
    )
    db.run(
        "DELETE FROM modified_races WHERE username = ?",
        [username]
    )


def get_text_bests(username, race_stats=False, universe="play", until=None):
    table = races_table_name(universe)
    if race_stats:
        text_bests = db.fetch(f"""
            SELECT text_id, wpm, number, timestamp, accuracy, points
            FROM (
                SELECT r.text_id, r.wpm, r.number, r.timestamp, r.accuracy, r.points,
                       ROW_NUMBER() OVER (PARTITION BY r.text_id ORDER BY r.wpm DESC) AS rn
                FROM {table} r
                INDEXED BY idx_{table}_username
                INNER JOIN (
                    SELECT text_id, MAX(wpm) AS max_wpm
                    FROM {table}
                    WHERE username = ?
                    GROUP BY text_id
                ) text_bests
                ON r.text_id = text_bests.text_id AND r.wpm = text_bests.max_wpm
                WHERE r.username = ?
            )
            WHERE rn = 1
            ORDER BY wpm DESC;
        """, [username, username])

    else:
        index = f"idx_{table}_username"
        if not until:
            index += "_text_id_wpm"
        timestamp_string = f"AND timestamp < {until}" if until else ""

        text_bests = db.fetch(f"""
            SELECT text_id, MAX(wpm) AS wpm
            FROM {table}
            INDEXED BY {index}
            WHERE username = ?
            {timestamp_string}
            GROUP BY text_id
            ORDER BY wpm DESC
        """, [username])

    return filter_disabled_texts(text_bests)


async def get_text_bests_time_travel(username, universe, user, race_stats=False):
    from database.races import get_races

    start_date = user["start_date"]
    end_date = user["end_date"]

    columns = ["text_id", "wpm", "number", "timestamp", "accuracy", "points"]
    if not race_stats:
        columns = columns[:2]

    race_list = await get_races(username, columns, start_date, end_date, universe=universe)
    text_bests = calculate_text_bests(race_list)

    return text_bests


def get_unraced_texts(username, universe="play"):
    from database.texts import get_texts
    table = races_table_name(universe)
    user_texts = db.fetch(f"""
        SELECT text_id FROM {table}
        INDEXED BY idx_{table}_username_text_id
        WHERE username = ?
        GROUP BY text_id
    """, [username])

    text_list = get_texts(include_disabled=False, universe=universe)
    user_text_set = set([text[0] for text in user_texts])
    unraced = [text for text in text_list if text["id"] not in user_text_set]

    return unraced


def count_races_over(username, category, threshold, over, universe, start_date=None, end_date=None):
    table = races_table_name(universe)

    times = db.fetch(f"""
        SELECT COUNT(*) FROM {table}
        INDEXED BY idx_{table}_username
        WHERE username = ?
        {get_date_query_string(start_date, end_date)}
        AND {category} {'>=' if over else '<'} {threshold}
    """, [username])[0][0]

    return times


def get_texts_over(username, threshold, category, universe, start_date=None, end_date=None):
    table = races_table_name(universe)
    threshold_string = f"HAVING TIMES >= {threshold}"
    category_string = f"AND {category} >= {threshold}"

    texts = db.fetch(f"""
        SELECT text_id, COUNT(text_id) AS times
        FROM {table}
        INDEXED BY idx_{table}_username_text_id_wpm
        WHERE username = ?
        {category_string if category != 'times' else ''}
        {get_date_query_string(start_date, end_date)}
        GROUP BY text_id
        {threshold_string if category == 'times' else ''}
        ORDER BY times DESC
    """, [username])

    return filter_disabled_texts(texts)


def get_texts_under(username, threshold, category, universe, start_date=None, end_date=None):
    table = races_table_name(universe)

    if category == "times":
        texts = db.fetch(f"""
            SELECT text_id, COUNT(text_id) AS times
            FROM {table}
            INDEXED BY idx_{table}_username_text_id
            WHERE username = ?
            {get_date_query_string(start_date, end_date)}
            GROUP BY text_id
            HAVING times < {threshold}
            ORDER BY times DESC
        """, [username])

    else:
        texts = db.fetch(f"""
            SELECT text_id, COUNT(text_id) AS times
            FROM {table}
            INDEXED BY idx_{table}_username_text_id
            WHERE username = ?
            {get_date_query_string(start_date, end_date)}
            AND text_id IN (
                SELECT text_id
                FROM {table}
                INDEXED BY idx_{table}_username_text_id{'_wpm' * (category == 'wpm')}
                WHERE username = ?
                {get_date_query_string(start_date, end_date)}
                GROUP BY text_id
                HAVING MAX({category}) < {threshold}
            )
            GROUP BY text_id
            ORDER BY times DESC
        """, [username, username])

    return filter_disabled_texts(texts)


def get_milestone_number(username, milestone, category, universe, start_date=None, end_date=None):
    table = races_table_name(universe)

    if category == "races":
        race = db.fetch(f"""
            SELECT number FROM {table}
            WHERE id = ?
            {get_date_query_string(start_date, end_date)}
        """, [strings.race_id(username, milestone)])
        if not race:
            return None
        return race[0][0]

    elif category == "wpm":
        race = db.fetch(f"""
            SELECT number FROM {table}
            INDEXED BY idx_{table}_username
            WHERE username = ?
            AND wpm >= ?
            {get_date_query_string(start_date, end_date)}
            ORDER BY timestamp ASC
            LIMIT 1
        """, [username, milestone])
        if not race:
            return None
        return race[0][0]

    elif category == "points":
        races = db.fetch(f"""
            SELECT number, points
            FROM {table}
            INDEXED BY idx_{table}_username
            WHERE username = ?
            {get_date_query_string(start_date, end_date)}
            ORDER BY timestamp ASC
        """, [username])

        total_points = 0
        for race in races:
            total_points += race[1]
            if total_points >= milestone:
                return race[0]
        return None

    else:
        disabled_text_ids = get_disabled_text_ids()
        unique_texts = set()
        races = db.fetch(f"""
            SELECT number, text_id
            FROM {table}
            INDEXED BY idx_{table}_username
            WHERE username = ?
            {get_date_query_string(start_date, end_date)}
            ORDER BY timestamp ASC
        """, [username])
        for race in races:
            if race[1] not in disabled_text_ids:
                unique_texts.add(race[1])
            if len(unique_texts) >= milestone:
                return race[0]
        return None


def correct_best_wpm(username):
    best_wpm = db.fetch("""
        SELECT wpm_best
        FROM users
        WHERE username = ?
    """, [username])[0][0]
    best_wpm = round(best_wpm, 2)

    actual_best_wpm = db.fetch("""
        SELECT wpm
        FROM races
        WHERE username = ?
        ORDER BY wpm DESC
        LIMIT 1
    """, [username])[0][0]

    if best_wpm > actual_best_wpm:
        db.run("""
            UPDATE users
            SET wpm_best = ?
            WHERE username = ?    
        """, [actual_best_wpm, username])


def get_disqualified_users():
    dq_users = db.fetch("""
        SELECT username
        FROM users
        WHERE disqualified = 1
    """)

    return [user[0] for user in dq_users]


def get_texts_typed(username):
    texts_typed = db.fetch("""
        SELECT DISTINCT text_id
        FROM races
        WHERE username = ?
    """, [username])

    return len(filter_disabled_texts(texts_typed))


def get_database_stats():
    stats = db.fetch("SELECT COUNT(races), SUM(races) FROM users")[0]

    return stats


def get_countries():
    users = db.fetch("SELECT username, country FROM users")

    country_dict = {}

    for user in users:
        country_dict[user['username']] = user['country']

    return country_dict


def get_universe_list():
    table_list = db.fetch("""
        SELECT name FROM sqlite_master
        WHERE type = 'table'
        AND name LIKE 'users_%'
    """)

    universe_list = ["_".join(table["name"].split("_")[1:]) for table in table_list]
    for i, universe in enumerate(universe_list):
        if universe in ["lang_zh_tw", "lang_sr_latn", "clickit_academy", "new_lang_zh_tw"]:
            underscore = universe.rfind("_")
            universe_list[i] = universe[:underscore] + "-" + universe[underscore + 1:]

    return universe_list
