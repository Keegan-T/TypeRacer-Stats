import utils
from database import db
import time

def get_disabled_texts():
    texts = db.fetch("""
        SELECT * FROM texts
        WHERE disabled = 1
    """)

    return texts


def add_user(username):
    db.run("""
        INSERT INTO users (username)
        VALUES (?)
    """, [username])


def get_users():
    users = db.fetch("SELECT * FROM users")

    return users


def get_user(username):
    user = db.fetch(
        "SELECT * FROM users WHERE username = ?",
        [username]
    )
    if not user: return None
    return user[0]


def get_usernames():
    users = db.fetch("SELECT username FROM users")

    return users


def get_users_from_list(usernames):
    users = db.fetch(
        f"""
            SELECT * FROM users
            WHERE username IN ({','.join(['?'] * len(usernames))})
        """,
        usernames
    )

    return users


def get_most(column, limit):
    top = db.fetch(
        f"""
            SELECT * FROM users
            WHERE disqualified = 0
            ORDER BY {column} DESC
            LIMIT ?
        """,
        [limit]
    )

    return top


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
    top = db.fetch(
        """
            SELECT * FROM users
            WHERE texts_typed >= 1000
            ORDER BY text_best_average DESC
            LIMIT ?
        """,
        [limit]
    )

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


def update_stats(user):
    db.run(
        """
            UPDATE users
            SET username = ?, display_name = ?, premium = ?, has_pic = ?, country = ?, joined = ?,
            wpm_average_all_time = ?, wpm_average_last_10 = ?, wpm_best = ?, wpm_verified = ?,
            races = ?, wins = ?, points = ?, points_retroactive = ?, seconds = ?, characters = ?, 
            avatar = ?, disqualified = ?, last_updated = ?
            WHERE username = ?
        """,
        (
            user['username'], user['display_name'], user['premium'], user['has_pic'], user['country'],
            user['joined'], user['wpm_average'], user['wpm_last_10'], user['wpm_best'], user['wpm_verified'],
            user['races'], user['wins'], user['points'], user['retroactive_points'], user['seconds'],
            user['characters'], user['avatar'], user['disqualified'], time.time(),
            user['username']
        )
    )


def update_text_stats(username, stats):
    db.run(
        """
            UPDATE users
            SET texts_typed = ?, text_best_average = ?, text_wpm_total = ?,
            max_quote_times = ?, max_quote_id = ?
            WHERE username = ? 
        """,
        [
            stats['texts_typed'], stats['text_best_average'], stats['text_wpm_total'],
            stats['max_quote_times'], stats['max_quote_id'],
            username
        ]
    )


def update_awards(username, first, second, third):
    db.run(
        """
            UPDATE users
            SET awards_first = ?, awards_second = ?, awards_third = ?
            WHERE username = ?
        """,
        [first, second, third, username]
    )


def delete_user(username):
    print(f"===== DELETING USER {username} =====")
    db.run(
        "DELETE FROM races WHERE username = ?",
        [username]
    )
    db.run(
        "DELETE FROM races_300 WHERE username = ?",
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


def get_last_updated(username):
    last_updated = db.fetch(
        """
            SELECT last_updated FROM users
            WHERE username = ?
        """,
        [username]
    )[0]['last_updated']

    return last_updated


def get_text_bests(username, race_stats=False):
    if race_stats:
        text_bests = db.fetch("""
            SELECT r.text_id, r.wpm, r.number, r.timestamp
            FROM races r
            INDEXED BY idx_races_username
            INNER JOIN (
                SELECT text_id, MAX(wpm) AS max_wpm
                FROM races
                WHERE username = ?
                GROUP BY text_id
            ) text_bests
            ON r.text_id = text_bests.text_id AND r.wpm = text_bests.max_wpm
            WHERE r.username = ?
            ORDER BY r.wpm DESC
        """, [username, username])

    else:
        text_bests = db.fetch("""
            SELECT text_id, MAX(wpm) AS wpm
            FROM races
            INDEXED BY idx_races_username_text_id_wpm
            WHERE username = ?
            GROUP BY text_id
            ORDER BY wpm DESC
        """, [username])

    disabled_text_ids = [text[0] for text in get_disabled_texts()]
    filtered_tb = [text for text in text_bests if text[0] not in disabled_text_ids]

    return filtered_tb


### Old version
# db.fetch(
#     """
#         WITH TextBests AS (
#           SELECT text_id, quote, wpm, number, timestamp, ROW_NUMBER() OVER (PARTITION BY text_id ORDER BY wpm DESC) AS row_num
#           FROM races
#           JOIN texts ON texts.id = races.text_id
#           WHERE username = 'keegant'
#         )
#         SELECT text_id, quote, wpm, number, timestamp
#         FROM TextBests
#         WHERE row_num = 1
#         ORDER BY wpm DESC
#     """
# )


def get_max_quote(username):
    max_quote = db.fetch(
        """
            SELECT text_id, COUNT(text_id) AS occurrences
            FROM races
            INDEXED BY idx_races_username_text_id
            WHERE username = ?
            GROUP BY text_id
            ORDER BY occurrences DESC
            LIMIT 1
        """,
        [username]
    )

    return max_quote[0]


def get_profile_picture_link(username):
    user = db.fetch(
        """
            SELECT has_pic, country
            FROM users
            WHERE username = ?
        """,
        [username]
    )

    info = user[0]
    if info['has_pic']:
        return f"https://data.typeracer.com/misc/pic?uid=tr:{username}"
    elif info['country']:
        return f"https://flagsapi.com/{info['country'].upper()}/flat/64.png"
    else:
        return "https://i.imgur.com/3fot7xB.png"


def get_words(username):
    words = db.fetch(
        """
            SELECT SUM(LENGTH(quote) - LENGTH(REPLACE(quote, ' ', '')) + 1) AS words
            FROM races
            JOIN texts ON texts.id = races.text_id
            WHERE username = ?
        """,
        [username]
    )[0]["words"]

    return words


def get_unraced_text_ids(username):
    user_texts = db.fetch("""
        SELECT text_id FROM races
        INDEXED BY idx_races_username_text_id
        WHERE username = ?
        GROUP BY text_id
    """, [username])

    texts = db.fetch("""
        SELECT * FROM texts
        WHERE disabled = 0
    """)

    user_text_set = set(user_texts)
    unraced = [text for text in texts if text[0] not in user_text_set]

    return unraced


def count_races_over(username, category, threshold, over=True):
    times = db.fetch(f"""
        SELECT COUNT(*) FROM races
        INDEXED BY idx_races_username
        WHERE username = ?
        AND {category} {'>=' if over else '<'} {threshold}
    """, [username])[0][0]

    return times


def get_texts_over(username, threshold, category):
    threshold_string = f"HAVING TIMES >= {threshold}"
    category_string = f"AND {category} >= {threshold}"
    texts = db.fetch(f"""
        SELECT text_id, COUNT(text_id) AS times
        FROM races
        INDEXED BY idx_races_username_text_id_wpm
        WHERE username = ?
        {category_string if category != 'times' else ''} 
        GROUP BY text_id
        {threshold_string if category == 'times' else ''}
        ORDER BY times DESC
    """, [username])

    disabled_text_ids = [text[0] for text in get_disabled_texts()]
    filtered_texts = [text for text in texts if text[0] not in disabled_text_ids]

    return filtered_texts


def get_texts_under(username, threshold, category=None):
    if category == "times":
        texts = db.fetch(f"""
            SELECT text_id, COUNT(text_id) AS times
            FROM races
            INDEXED BY idx_races_username_text_id
            WHERE username = ?
            GROUP BY text_id
            HAVING times < {threshold}
            ORDER BY times DESC
        """, [username])

    else:
        texts = db.fetch(f"""
            SELECT text_id, COUNT(text_id) AS times
            FROM races
            INDEXED BY idx_races_username_text_id
            WHERE username = ?
            AND text_id IN (
                SELECT text_id
                FROM races
                INDEXED BY idx_races_username_text_id{'_wpm' * (category == 'wpm')}
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

def get_milestone_number(username, milestone, category):
    if category == "races":
        race = db.fetch("""
            SELECT number FROM races
            WHERE id = ?
        """, [utils.race_id(username, milestone)])
        if not race:
            return None
        return race[0][0]

    elif category == "wpm":
        race = db.fetch("""
            SELECT number FROM races
            INDEXED BY idx_races_username
            WHERE username = ?
            AND wpm >= ?
            ORDER BY timestamp ASC
            LIMIT 1
        """, [username, milestone])
        if not race:
            return None
        return race[0][0]

    elif category == "points":
        races = db.fetch("""
            SELECT number, points
            FROM races
            INDEXED BY idx_races_username
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
        races = db.fetch("""
            SELECT number, text_id
            FROM races
            INDEXED BY idx_races_username
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

def get_stats():
    stats = db.fetch("SELECT COUNT(races), SUM(races) FROM users")[0]

    return stats

def get_countries():
    users = db.fetch("SELECT username, country FROM users")

    country_dict = {}

    for user in users:
        country_dict[user['username']] = user['country']

    return country_dict