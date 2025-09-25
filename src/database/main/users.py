import time

from database.main import texts, db
from database.main.races import maintrack_text_pool
from database.main.texts import filter_disabled, get_disabled_text_ids
from utils import dates
from utils.logging import log
from utils.stats import get_text_stats, calculate_text_bests, calculate_total_performance
from utils.strings import get_date_query_string


def create_user_data(racer):
    db.run("""
        INSERT INTO users (username, joined) VALUES (?, ?)
    """, [racer["username"], racer["joined_at"]])


def create_user_stats(racer):
    db.run("""
        INSERT INTO user_stats
        (universe, username, points_retroactive, total_time, characters, last_accessed)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, [racer["universe"], racer["username"], 0, 0, 0])


def update_user_data(racer):
    db.run("""
        UPDATE users
        SET display_name = ?, premium = ?, country = ?,
        avatar = ?, last_updated = ?
        WHERE username = ?
    """, [
        racer["name"], bool(racer["premium"]), racer["country"],
        racer["avatar"], dates.now().timestamp(), racer["username"],
    ])


def update_user_stats(racer):
    db.run("""
        UPDATE user_stats
        SET wpm_average = ?, wpm_best = ?, wpm_verified = ?,
        races = ?, wins = ?, points = ?, disqualified = ?
        WHERE universe = ?
        AND username = ?
    """, [
        racer["avg_wpm"], racer["best_wpm"], racer["cert_wpm"], racer["total_races"],
        racer["total_wins"], racer["points"], racer["dqd"], racer["universe"], racer["username"],
    ])


def update_user_aggregate_stats(username, universe, points_retroactive, total_time, characters):
    db.run("""
        UPDATE user_stats
        SET
            points_retroactive = points_retroactive + ?,
            total_time = total_time + ?,
            characters = characters + ?
        WHERE universe = ?
        AND username = ?
    """, [
        points_retroactive, total_time, characters,
        universe, username
    ])


def get_user(username, universe="play"):
    user = db.fetch("""
        SELECT users.*, user_stats.* FROM users
        JOIN user_stats USING (username)
        WHERE universe = ?
        AND username = ?
    """, [universe, username])
    if not user:
        return None
    elif user[0]["races"] == 0 or not user[0]["last_updated"]:
        return None
    return user[0]


async def get_important_users():
    users = (
        get_most("races", 20)
        + get_most_daily_races(20)
        + get_most("characters", 20)
        + get_most("total_time", 20)
        + get_most_total_points(20)
        + get_most_daily_points(20)
        + get_top_text_best(20)
        + get_most("text_wpm_total", 20)
        + get_most("texts_typed", 20)
        + get_most("text_repeat_times", 20)
        + get_most_awards(20)
    )

    return list(set([user["username"] for user in users]))


def get_user_data(username):
    user = db.fetch("""
        SELECT * FROM users
        WHERE username = ?
    """, [username])

    if not user:
        return {}

    return dict(user[0])


def get_user_stats(username, universe):
    user = db.fetch("""
        SELECT * FROM user_stats
        WHERE universe = ?
        AND username = ?
    """, [universe, username])

    if not user:
        return {}

    return dict(user[0])


def update_last_accessed(universe, username):
    db.run("""
        UPDATE user_stats
        SET last_accessed = datetime('now')
        WHERE universe = ?
        AND username = ?
    """, [universe, username])


async def delete_expired_users():
    important_users = get_important_users()

    users = db.fetch("""
        SELECT universe, username FROM user_stats
        WHERE last_accessed < datetime('now', '-30 days')
    """)

    for user in users:
        username = user["username"]
        if username not in important_users:
            log(f"Deleting expired user {username}")
            await delete_user(user["username"], user["universe"])


async def filter_stats(stats, user):
    from database.main.races import get_races
    stats = dict(stats)
    username = stats["username"]
    universe = user["universe"]
    start_date = user["start_date"]
    end_date = user["end_date"]
    text_pool = user["settings"]["text_pool"]
    columns = ["*"]
    race_list = await get_races(username, columns, start_date, end_date, universe=universe, text_pool=text_pool)
    text_bests = calculate_text_bests(race_list)

    races = len(race_list)
    points = 0
    wins = 0
    total_wpm = 0
    best_wpm = 0
    for race in race_list:
        points += race["points"]
        wins += 1 if (race["rank"] == 1 and race["racers"] > 1) else 0
        total_wpm += race["wpm_adjusted"]
        best_wpm = max(race["wpm_adjusted"], best_wpm)
    average_wpm = total_wpm / len(race_list) if race_list else 0

    stats["races"] = stats["total_races"] = races
    stats["points"] = points
    stats["wins"] = stats["total_wins"] = wins
    stats["wpm_average"] = stats["avg_wpm"] = average_wpm
    stats["wpm_best"] = stats["best_wpm"] = best_wpm
    stats["text_wpm_total"] = sum([text["wpm"] for text in text_bests])
    stats["texts_typed"] = len(text_bests)
    stats["text_best_average"] = stats["text_wpm_total"] / stats["texts_typed"] if text_bests else 0

    return stats


def get_most(column, limit):
    top = db.fetch(f"""
        SELECT users.*, user_stats.* FROM users
        JOIN user_stats USING (username)
        WHERE universe = "play"
        AND disqualified = 0
        ORDER BY {column} DESC
        LIMIT ?
    """, [limit])

    return top


def get_most_texts_typed(limit):
    leaders = get_most("texts_typed", limit)
    text_count = texts.get_text_count()
    disabled = get_disabled_text_ids()

    results = []
    for user in leaders:
        user = dict(user)
        min_repeats = 1
        if user["texts_typed"] == text_count:
            min_repeats = float("inf")
            repeats = db.fetch("""
                SELECT text_id, COUNT(*) as times_typed
                FROM races
                WHERE universe = "play"
                AND username = ?
                GROUP BY text_id
                ORDER BY times_typed DESC
            """, [user["username"]])
            for text in repeats:
                if text["text_id"] in disabled:
                    continue
                min_repeats = min(min_repeats, text["times_typed"])
        user["min_repeats"] = min_repeats
        results.append(user)

    results.sort(key=lambda u: (u["min_repeats"], u["texts_typed"]), reverse=True)

    return results


def get_most_daily_races(limit):
    top = db.fetch("""
        SELECT users.*, user_stats.*,
            CAST (races AS REAL) / (CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1)
            AS daily_races,
            CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1 AS days
        FROM users
        JOIN user_stats USING (username)
        WHERE universe = "play"
        AND CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1 >= 90
        ORDER BY daily_races DESC
        LIMIT ?
    """, [limit])

    return top


def get_most_daily_points(limit):
    top = db.fetch("""
        SELECT users.*, user_stats.*,
            (points + points_retroactive) AS points_total,
            (points + points_retroactive) / (CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1)
            AS daily_points,
            CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1 AS days
        FROM users
        JOIN user_stats USING (username)
        WHERE universe = "play"
        AND CAST(julianday('now') - julianday(datetime(joined, 'unixepoch')) AS INTEGER) + 1 >= 90
        ORDER BY daily_points DESC
        LIMIT ?
    """, [limit])

    return top


def get_most_total_points(limit):
    top = db.fetch("""
        SELECT users.*, user_stats.*, (points + points_retroactive) AS points_total    
        FROM users
        JOIN user_stats USING (username)
        WHERE universe = "play"
        ORDER BY points_total DESC
        LIMIT ?
    """, [limit])

    return top


def get_top_text_best(limit):
    from database.main.texts import get_text_count
    text_count = get_text_count()
    min_texts = int(text_count * 0.2)
    top = db.fetch("""
        SELECT users.*, user_stats.*
        FROM users
        JOIN user_stats USING (username)
        WHERE universe = "play"
        AND texts_typed >= ?
        AND disqualified = 0
        ORDER BY text_best_average DESC
        LIMIT ?
    """, [min_texts, limit])

    return top


def get_most_awards(limit):
    top = db.fetch("""
        SELECT *, (awards_first + awards_second + awards_third) as awards_total
        FROM users
        ORDER BY awards_total DESC
        LIMIT ?
    """, [limit])

    return top


async def get_most_texts_over(wpm, limit=10):
    top = await db.fetch_async("""
        SELECT r.username, u.country, COUNT(DISTINCT text_id) AS texts_over
        FROM races r
        JOIN users u USING (username)
        WHERE universe = "play"
        AND wpm_adjusted >= ?
        GROUP BY username
    """, [wpm])

    banned = get_disqualified_users()
    top.sort(key=lambda x: -x["texts_over"])
    filtered = []
    i = 0
    for user in top:
        if user["username"] in banned:
            continue
        filtered.append(user)
        i += 1
        if i == limit:
            break

    return filtered


async def get_most_races_over(wpm, limit=10):
    top = await db.fetch_async("""
        SELECT r.username, u.country, COUNT(username) AS races_over
        FROM races r
        JOIN users u USING (username)
        WHERE universe = "play"
        AND wpm_adjusted >= ?
        GROUP BY username
    """, [wpm])

    banned = get_disqualified_users()
    top.sort(key=lambda x: -x["races_over"])
    filtered = []
    i = 0
    for user in top:
        if user["username"] in banned:
            continue
        filtered.append(user)
        i += 1
        if i == limit:
            break

    return filtered


async def get_most_performance():
    text_list = texts.get_texts(as_dictionary=True)
    user_list = await db.fetch_async("""
        SELECT * FROM user_stats
        WHERE universe = "play"
        AND text_best_average > 170
        AND disqualified = 0
    """)

    top = []
    for i, user in enumerate(user_list):
        text_bests = get_text_bests(user["username"])
        performance = calculate_total_performance(text_bests, text_list)
        top.append({**user, "performance": performance})
    top.sort(key=lambda x: -x["performance"])

    return top


def update_user(username, display_name, premium, country, avatar):
    db.run("""
        UPDATE users
        SET display_name = ?, premium = ?, country = ?, avatar = ?, last_updated = ?
        WHERE username = ?
    """, [display_name, premium, country, avatar, time.time(), username])


def update_stats(universe, username, wpm_average, wpm_best, wpm_verified, races,
                 wins, points, points_retroactive, total_time, characters, disqualified):
    db.run(f"""
        UPDATE user_stats
        SET wpm_average = ?, wpm_best = ?, wpm_verified = ?, races = ?, wins = ?, points = ?,
        points_retroactive = ?, total_time = ?, characters = ?, disqualified = ?
        WHERE universe = ?
        AND username = ?
    """, [
        wpm_average, wpm_best, wpm_verified, races, wins, points,
        points_retroactive, total_time, characters, disqualified,
        universe, username
    ])


def update_text_stats(username, universe):
    text_bests = get_text_bests(username, universe=universe)
    repeated_quote = get_repeated_quote(username, universe)
    stats = get_text_stats(text_bests)

    db.run(f"""
        UPDATE user_stats
        SET texts_typed = ?, text_best_average = ?, text_wpm_total = ?,
        text_repeat_times = ?, text_repeat_id = ?
        WHERE universe = ?
        AND username = ?
    """, [
        stats["texts_typed"], stats["text_best_average"], stats["text_wpm_total"],
        repeated_quote["times_typed"], repeated_quote["text_id"],
        universe, username
    ])


def update_awards(username, first, second, third):
    db.run("""
        UPDATE users
        SET awards_first = ?, awards_second = ?, awards_third = ?
        WHERE username = ?
    """, [first, second, third, username])


async def delete_user(username, universe):
    log(f"Deleting user: {username} (Universe: {universe})")
    db.run("""
        DELETE FROM user_stats
        WHERE universe = ?
        AND username = ?
    """, [universe, username])

    db.run("""
        DELETE FROM races
        WHERE universe = ?
        AND username = ?
    """, [universe, username])

    db.run("""
        DELETE FROM typing_logs
        WHERE universe = ?
        AND username = ?
    """, [universe, username])

    if universe == "play":
        db.run("DELETE FROM text_results WHERE username = ?", [username])


def get_text_bests(username, race_stats=False, universe="play", until=None, wpm="wpm", text_pool="all"):
    columns = "text_id"
    if race_stats:
        columns = f"text_id, {wpm} AS wpm, number, timestamp, accuracy, points"
    timestamp_string = f"AND timestamp < {until}" if until else ""
    text_pool_string = (
        f"AND text_id IN ({",".join([str(tid) for tid in maintrack_text_pool])})"
        if text_pool != "all" and universe == "play" else ""
    )
    column_filter = ""
    if wpm in ["wpm_raw", "wpm_pauseless"]:
        column_filter = f"AND {wpm} IS NOT NULL"

    text_bests = db.fetch(f"""
        SELECT {columns}, MAX({wpm}) AS wpm
        FROM races
        WHERE universe = ?
        AND username = ?
        {column_filter}
        {timestamp_string}
        {text_pool_string}
        GROUP BY text_id
        ORDER BY {wpm} DESC
    """, [universe, username])

    return filter_disabled(text_bests)


async def get_text_bests_time_travel(username, universe, user, race_stats=False, wpm="wpm", text_pool="all"):
    from database.main.races import get_races

    start_date = user["start_date"]
    end_date = user["end_date"]

    columns = ["text_id", wpm, "number", "timestamp", "accuracy", "points"]
    if not race_stats:
        columns = columns[:2]

    race_list = await get_races(username, columns, start_date, end_date, universe=universe, text_pool=text_pool)
    text_bests = calculate_text_bests(race_list)

    return text_bests


def get_repeated_quote(username, universe):
    repeated_quote = db.fetch(f"""
        SELECT text_id, COUNT(*) AS times_typed
        FROM races
        WHERE universe = ?
        AND username = ?
        GROUP BY text_id
        ORDER BY times_typed DESC
    """, [universe, username])[0]

    return repeated_quote


def get_unraced_texts(username, universe="play", text_pool="all"):
    from database.main.texts import get_texts
    text_pool_string = (
        f"AND text_id IN ({",".join([str(tid) for tid in maintrack_text_pool])})"
        if text_pool != "all" and universe == "play" else ""
    )

    user_texts = db.fetch(f"""
        SELECT DISTINCT(text_id)
        FROM races
        INDEXED BY idx_races_universe_username_text_id
        WHERE universe = ?
        AND username = ?
        {text_pool_string}
    """, [universe, username])

    user_texts = set([text["text_id"] for text in user_texts])
    text_list = get_texts(get_disabled=False, universe=universe, text_pool=text_pool)

    return [text for text in text_list if text["text_id"] not in user_texts]


def count_races_over(username, threshold, category, over, universe, start_date=None, end_date=None, text_pool="all"):
    text_pool_string = (
        f"AND text_id IN ({",".join([str(tid) for tid in maintrack_text_pool])})"
        if text_pool != "all" and universe == "play" else ""
    )

    times = db.fetch(f"""
        SELECT COUNT(*)
        FROM races
        INDEXED BY idx_races_universe_username
        WHERE universe = ?
        AND username = ?
        {text_pool_string} 
        {get_date_query_string(start_date, end_date)}
        AND {category} {'>=' if over else '<'} {threshold}
    """, [universe, username])[0][0]

    return times


def get_texts_over(username, threshold, category, universe, start_date=None, end_date=None, text_pool="all"):
    threshold_string = f"HAVING TIMES >= {threshold}" * (category == "times")
    category_string = f"AND {category} >= {threshold}" * (category != "times")
    index = f"INDEXED BY idx_races_universe_username" * (category == "points")
    text_pool_string = (
        f"AND text_id IN ({",".join([str(tid) for tid in maintrack_text_pool])})"
        if text_pool != "all" and universe == "play" else ""
    )

    texts = db.fetch(f"""
        SELECT text_id, COUNT(text_id) AS times
        FROM races
        {index}
        WHERE universe = ?
        AND username = ?
        {category_string}
        {get_date_query_string(start_date, end_date)}
        {text_pool_string}
        GROUP BY text_id
        {threshold_string}
        ORDER BY times DESC
    """, [universe, username])

    return filter_disabled(texts)


def get_texts_under(username, threshold, category, universe, start_date=None, end_date=None, text_pool="all"):
    if category == "wpm":
        category = "wpm_adjusted"
    text_pool_string = (
        f"AND text_id IN ({",".join([str(tid) for tid in maintrack_text_pool])})"
        if text_pool != "all" and universe == "play" else ""
    )

    if category == "times":
        texts = db.fetch(f"""
            SELECT text_id, COUNT(text_id) AS times
            FROM races
            WHERE universe = ?
            AND username = ?
            {get_date_query_string(start_date, end_date)}
            {text_pool_string}
            GROUP BY text_id
            HAVING times < {threshold}
            ORDER BY times DESC
        """, [universe, username])

    else:
        texts = db.fetch(f"""
            SELECT text_id, COUNT(text_id) AS times
            FROM races
            INDEXED BY idx_races_universe_username_text_id
            WHERE universe = ?
            AND username = ?
            {get_date_query_string(start_date, end_date)}
            AND text_id IN (
                SELECT text_id
                FROM races
                INDEXED BY idx_races_universe_username_text_id{'_wpm' * (category == 'wpm')}
                WHERE universe = ?
                AND username = ?
                {get_date_query_string(start_date, end_date)}
                GROUP BY text_id
                HAVING MAX({category}) < {threshold}
            )
            {text_pool_string}
            GROUP BY text_id
            ORDER BY times DESC
        """, [universe, username, universe, username])

    return filter_disabled(texts)


def get_milestone_number(username, milestone, category, universe, start_date=None, end_date=None):
    if category == "races":
        race = db.fetch(f"""
            SELECT number
            FROM races
            WHERE universe = ?
            AND username = ?
            AND number = ?
            {get_date_query_string(start_date, end_date)}
        """, [universe, username, milestone])
        if not race:
            return None
        return race[0][0]

    elif category == "wpm":
        race = db.fetch(f"""
            SELECT number
            FROM races
            INDEXED BY idx_races_universe_username
            WHERE universe = ?
            AND username = ?
            AND wpm_adjusted >= ?
            {get_date_query_string(start_date, end_date)}
            ORDER BY timestamp ASC
            LIMIT 1
        """, [universe, username, milestone])
        if not race:
            return None
        return race[0][0]

    elif category == "points":
        races = db.fetch(f"""
            SELECT number, points
            FROM races
            INDEXED BY idx_races_universe_username
            WHERE universe = ?
            AND username = ?
            {get_date_query_string(start_date, end_date)}
            ORDER BY timestamp ASC
        """, [universe, username])

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
            FROM races
            INDEXED BY idx_races_universe_username
            WHERE universe = ?
            AND username = ?
            {get_date_query_string(start_date, end_date)}
            ORDER BY timestamp ASC
        """, [universe, username])
        for race in races:
            if race[1] not in disabled_text_ids:
                unique_texts.add(race[1])
            if len(unique_texts) >= milestone:
                return race[0]
        return None


def get_disqualified_users(universe="play"):
    dq_users = db.fetch("""
        SELECT username
        FROM user_stats
        WHERE universe = ?
        AND disqualified = 1
    """, [universe])

    return [user[0] for user in dq_users]


def get_database_stats():
    race_count = db.fetch("SELECT COUNT(rowid) FROM races")[0][0]
    text_count = db.fetch("SELECT COUNT(rowid) FROM texts")[0][0]
    user_count = db.fetch("SELECT COUNT(rowid) FROM users")[0][0]
    universe_count = db.fetch("SELECT COUNT(DISTINCT universe) FROM user_stats")[0][0]

    return race_count, text_count, user_count, universe_count


def get_countries():
    users = db.fetch("SELECT username, country FROM users")

    return {
        user["username"]: user["country"]
        for user in users
    }


def get_universe_list():
    universe_list = db.fetch("""
        SELECT DISTINCT universe
        FROM text_universes
    """)

    return [universe["universe"] for universe in universe_list]
