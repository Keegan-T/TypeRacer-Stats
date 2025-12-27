from urllib.parse import urlparse


def get_url_info(url):
    result = urlparse(url)
    if not (result.netloc and result.scheme):
        return None
    try:
        parts = url.replace("%7c", "|").replace("%7C", "|").split("|")
        universe = parts[-3].split("?id=")[1]
        if not universe:
            universe = "play"
        username = parts[-2][3:]
        race_number = int(parts[-1].split("&")[0])

        return username, race_number, universe
    except Exception:
        return None


def replay(username, race_number, universe="play", dq=False, timestamp=0):
    """
    Generates a replay URL for a race.

    Uses custom URL (typeracer.keegant.dev) for races older than 2 years,
    since the official TypeRacer URL only works for races < 2 years old.

    Args:
        username: TypeRacer username
        race_number: Race number
        universe: Universe (default "play")
        dq: Include allowDisqualified parameter (default False)
        timestamp: Race timestamp (Unix timestamp). If 0 or not provided,
                   uses official URL by default.

    Returns:
        URL string for the race replay
    """
    # Check if race is older than 2 years
    from utils.dates import now
    two_years = 365 * 86400 * 2

    if now().timestamp() - timestamp > two_years:
        # Use custom URL for old races (official URL doesn't work)
        url = f"http://typeracer.keegant.dev/race/{username}/{race_number}"
        if universe != "play":
            url += f"?universe={universe}"
        return url

    # Use official TypeRacer URL for recent races (or when timestamp not provided)
    universe_param = "" if universe == "play" else universe
    url = f"https://data.typeracer.com/pit/result?id={universe_param}%7Ctr:{username}%7C{race_number}"
    if dq:
        url += "&allowDisqualified=true"

    return url


def ghost(text_id, universe="play"):
    if universe != "play":
        return f"https://play.typeracer.com/?ghost={universe}%7Cbot%3A1%7C{text_id}&universe={universe}"

    return f"https://play.typeracer.com/?ghost=%7Cbot%3A1%7C{text_id}"


def profile(username, universe="play"):
    if universe != "play":
        return f"https://data.typeracer.com/pit/profile?user={username}&universe={universe}"

    return f"https://data.typeracer.com/pit/profile?user={username}"


def profile_picture(username):
    return f"https://data.typeracer.com/misc/pic?uid=tr:{username}"


def competition(date, period, sort, results_per_page, universe):
    sort = {
        "races": "gamesFinished",
        "points": "points",
        "wpm": "wpm",
        "best": "bestGameWpm",
        "accuracy": "accuracy",
    }.get(sort, "points")
    date_string = date.strftime("%Y-%m-%d")
    results_per_page = max(results_per_page, 10)

    return (
        f"https://data.typeracer.com/pit/competitions?date={date_string}"
        f"&sort={sort}&kind={period}&n={results_per_page}&universe={universe}"
    )


def games(username, start_time, end_time, races_per_page, universe="play"):
    return (
        f"https://data.typeracer.com/games?playerId=tr:{username}&startDate={start_time}"
        f"&endDate={end_time}&n={races_per_page}&universe={universe}"
    )


def text_info(text_id):
    return f"https://data.typeracer.com/pit/text_info?id={text_id}"


def trdata_text_list(universe):
    return f"https://typeracerdata.com/texts?sort=id&texts=full&universe={universe}"


def trdata_text_analysis(username, universe="play"):
    url = f"https://typeracerdata.com/text.analysis?username={username}"
    if universe != "play":
        url += f"&universe={universe}"

    return url


def trdata_text(text_id, universe="play"):
    url = f"https://typeracerdata.com/text?id={text_id}"
    if universe != "play":
        url += f"&universe={universe}"

    return url


def trdata_compare(username1, username2, universe="play"):
    url = f"https://www.typeracerdata.com/comparison?username1={username1}&username2={username2}"
    if universe != "play":
        url += f"&universe={universe}"

    return url


def trdata_text_races(username, text_id, universe="play"):
    url = f"https://typeracerdata.com/text.races?username={username}&text={text_id}"
    if universe != "play":
        url += f"&universe={universe}"

    return url
