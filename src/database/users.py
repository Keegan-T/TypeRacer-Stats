import time

from database import db
from utils import strings
from utils.logging import log
from utils.stats import get_text_stats


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


def get_disabled_texts():
    texts = db.fetch("""
        SELECT * FROM texts
        WHERE disabled = 1
    """)

    return texts


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


def get_most(column, limit):
    top = db.fetch(f"""
        SELECT * FROM users
        WHERE disqualified = 0
        ORDER BY {column} DESC
        LIMIT ?
    """, [limit])

    return top


async def get_most_text_repeats(limit):
    top = await db.fetch_async("""
        SELECT username, text_id, MAX(times_typed) AS max_times
        FROM (
            SELECT username, text_id, COUNT(*) AS times_typed
            FROM races
            INDEXED BY idx_races_username_text_id
            GROUP BY username, text_id
            ORDER BY times_typed DESC
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


def get_text_bests(username, race_stats=False, universe="play"):
    table = races_table_name(universe)
    if race_stats:
        text_bests = db.fetch(f"""
            SELECT text_id, wpm, number, timestamp, accuracy
            FROM (
                SELECT r.text_id, r.wpm, r.number, r.timestamp, r.accuracy,
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
        text_bests = db.fetch(f"""
            SELECT text_id, MAX(wpm) AS wpm
            FROM {table}
            INDEXED BY idx_{table}_username_text_id_wpm
            WHERE username = ?
            GROUP BY text_id
            ORDER BY wpm DESC
        """, [username])

    disabled_text_ids = [text[0] for text in get_disabled_texts()]
    filtered_tb = [text for text in text_bests if text[0] not in disabled_text_ids]

    return filtered_tb


def get_unraced_text_ids(username, universe):
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


def count_races_over(username, category, threshold, over, universe):
    table = races_table_name(universe)
    times = db.fetch(f"""
        SELECT COUNT(*) FROM {table}
        INDEXED BY idx_{table}_username
        WHERE username = ?
        AND {category} {'>=' if over else '<'} {threshold}
    """, [username])[0][0]

    return times


def get_texts_over(username, threshold, category, universe):
    table = races_table_name(universe)
    threshold_string = f"HAVING TIMES >= {threshold}"
    category_string = f"AND {category} >= {threshold}"
    texts = db.fetch(f"""
        SELECT text_id, COUNT(text_id) AS times
        FROM {table}
        INDEXED BY idx_{table}_username_text_id_wpm
        WHERE username = ?
        {category_string if category != 'times' else ''} 
        GROUP BY text_id
        {threshold_string if category == 'times' else ''}
        ORDER BY times DESC
    """, [username])

    disabled_text_ids = [text[0] for text in get_disabled_texts()]
    filtered_texts = [text for text in texts if text[0] not in disabled_text_ids]

    return filtered_texts


def get_texts_under(username, threshold, category, universe):
    table = races_table_name(universe)
    if category == "times":
        texts = db.fetch(f"""
            SELECT text_id, COUNT(text_id) AS times
            FROM {table}
            INDEXED BY idx_{table}_username_text_id
            WHERE username = ?
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
            AND text_id IN (
                SELECT text_id
                FROM {table}
                INDEXED BY idx_{table}_username_text_id{'_wpm' * (category == 'wpm')}
                WHERE username = ?
                GROUP BY text_id
                HAVING MAX({category}) < {threshold}
            )
            GROUP BY text_id
            ORDER BY times DESC
        """, [username, username])

    disabled_text_ids = [text[0] for text in get_disabled_texts()]
    filtered_texts = [text for text in texts if text[0] not in disabled_text_ids]

    return filtered_texts


def get_milestone_number(username, milestone, category, universe):
    table = races_table_name(universe)
    if category == "races":
        race = db.fetch(f"""
            SELECT number FROM {table}
            WHERE id = ?
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
            ORDER BY timestamp ASC
        """, [username])

        total_points = 0
        for race in races:
            total_points += race[1]
            if total_points >= milestone:
                return race[0]
        return None

    else:
        disabled_ids = [text[0] for text in get_disabled_texts()]
        unique_texts = set()
        races = db.fetch(f"""
            SELECT number, text_id
            FROM {table}
            INDEXED BY idx_{table}_username
            WHERE username = ?
            ORDER BY timestamp ASC
        """, [username])
        for race in races:
            if race[1] not in disabled_ids:
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

    disabled_text_ids = [text[0] for text in get_disabled_texts()]

    filtered_texts_typed = []
    for text in texts_typed:
        if text[0] not in disabled_text_ids:
            filtered_texts_typed.append(text[0])

    return len(filtered_texts_typed)


def get_database_stats():
    stats = db.fetch("SELECT COUNT(races), SUM(races) FROM users")[0]

    return stats


def get_countries():
    users = db.fetch("SELECT username, country FROM users")

    country_dict = {}

    for user in users:
        country_dict[user['username']] = user['country']

    return country_dict
