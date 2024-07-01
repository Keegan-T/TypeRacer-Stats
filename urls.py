def replay(username, race_number, universe="play"):
    if universe == "play":
        universe = ""
    return f"https://data.typeracer.com/pit/result?id={universe}%7Ctr:{username}%7C{race_number}"


def ghost(username, race_number, universe="play"):
    if universe != "play":
        return f"https://play.typeracer.com/?ghost={universe}%7Ctr:{username}%7C{race_number}&universe={universe}"

    return f"https://play.typeracer.com/?ghost=%7Ctr%3A{username}%7C{race_number}"


def profile(username, universe):
    if universe != "play":
        return f"https://data.typeracer.com/pit/profile?user={username}&universe={universe}"

    return f"https://data.typeracer.com/pit/profile?user={username}"


def profile_picture(username):
    return f"https://data.typeracer.com/misc/pic?uid=tr:{username}"


def top_10(text_id, universe="play"):
    return f"https://data.typeracer.com/textstats?textId={text_id}&distinct=1&universe={universe}&playerId=a"


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