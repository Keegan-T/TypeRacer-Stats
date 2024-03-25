def replay(username, race_number, universe="play"):
    if universe == "play":
        universe = ""
    return f"https://data.typeracer.com/pit/result?id={universe}|tr:{username}|{race_number}"


def ghost(username, race_number):
    return f"https://play.typeracer.com/?ghost=%7Ctr%3A{username}%7C{race_number}"


def profile(username):
    return f"https://data.typeracer.com/pit/profile?user={username}"


def profile_picture(username):
    return f"https://data.typeracer.com/misc/pic?uid=tr:{username}"


def top_10(text_id):
    return f"https://data.typeracer.com/textstats?textId={text_id}&distinct=1&universe=play&playerId=a"


def trdata_text(text_id):
    return f"https://typeracerdata.com/text?id={text_id}"


def trdata_compare(username1, username2):
    return f"https://www.typeracerdata.com/comparison?username1={username1}&username2={username2}"


def trdata_text_races(username, text_id):
    return f"https://typeracerdata.com/text.races?username={username}&text={text_id}"
