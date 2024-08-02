import json


def get_alts():
    with open("./data/alts.json") as file:
        joined_accounts = json.loads(file.read())

    alts = {}
    for usernames in joined_accounts:
        for username in usernames:
            alts[username] = usernames

    return alts
