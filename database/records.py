from discord import Embed
from datetime import datetime
import json
import utils
import colors
import database.races_300 as races_300
import database.users as users
from config import records_channel

medals = [":first_place:", ":second_place:", ":third_place:"]
countries = {}
exclude_300s = {
    "izanagiii",
    "i_dont_know_you_know",
    "taran",
    "slowaccount",
}


def get_countries():
    global countries
    countries = users.get_countries()
    countries["taran"] = "us"
    countries["taran127"] = "us"
    countries["tedioustuna47"] = "us"
    countries["mispelled"] = "us"
    countries["arabianghosthaunting"] = "ph"
    countries["wordracer888"] = "au"
    countries["deroche1"] = "us"
    countries["jestercaporado"] = "ph"
    countries["yukomiya"] = "au"


async def update(bot):
    print("Updating TypeRacer Records...")
    channel = bot.get_channel(records_channel)
    message_history = channel.history(limit=None)
    messages = []
    async for message in message_history:
        if message.author == bot.user:
            messages.append(message.id)

    messages.reverse()

    records = get_records()

    # No messages, mounting for the first time
    if not messages:
        for embed in records:
            await channel.send(embed=embed)

    # Updating existing messages
    else:
        record_list = iter(records)
        for message_id in messages:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=next(record_list))

    print("Finished Updating Records")

async def update_300_club(bot):
    get_countries()
    print("Updating 300 Club...")
    channel = bot.get_channel(records_channel)
    message_history = channel.history(limit=None)
    messages = []
    async for message in message_history:
        if message.author == bot.user:
            messages.append(message.id)

    messages.reverse()

    club_300_1, club_300_2 = club_300()

    records = [
        club_400(),
        club_300_1,
        club_300_2,
    ]

    # Records are not mounted
    if not messages:
        return

    # Updating existing messages
    else:
        record_list = iter(records)
        for message_id in messages[1:4]:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=next(record_list))

    print("Updated 300 Club")

def get_records():
    date = datetime.now()
    get_countries()

    last_updated = Embed(
        title="Last Updated",
        description=utils.discord_timestamp(date.timestamp(), "d"),
        color=colors.gold,
    )

    club_300_1, club_300_2 = club_300()

    embeds = [
        speed_records(),
        club_400(),
        club_300_1,
        club_300_2,
        race_records(),
        point_records(),
        speedrun_records(),
        text_records(),
        award_records(),
        last_updated,
    ]

    return embeds


def speed_records():
    file = open("./data/records.json", "r")
    data = json.loads(file.read())
    records = data['speed']

    embed = Embed(title="Speed Records", color=colors.gold)

    embed.add_field(
        name=records[0]['record'],
        value=f"{get_flag(records[0]['username'])}{records[0]['username']} - "
              f"[{records[0]['unlagged']} WPM]"
              f"(https://data.typeracer.com/pit/result?id=|tr:{records[0]['username']}|{records[0]['race']}) "
              f"({records[0]['lagged']} WPM Lagged) - {records[0]['date']}",
        inline=False
    )

    embed.add_field(
        name=records[1]['record'],
        value=f"{get_flag(records[1]['username'])}{records[1]['username']} - "
              f"[{records[1]['adjusted']} WPM]"
              f"(https://data.typeracer.com/pit/result?id=|tr:{records[1]['username']}|{records[1]['race']}) - "
              f"{records[1]['date']}",
        inline=False
    )

    embed.add_field(
        name=records[2]['record'],
        value=f"{get_flag(records[2]['username'])}{records[2]['username']} - "
              f"[{records[2]['unlagged']} WPM]"
              f"(https://data.typeracer.com/pit/result?id=|tr:{records[2]['username']}|{records[2]['race']}) "
              f"({records[2]['lagged']} WPM Lagged) - {records[2]['date']}",
        inline=False
    )

    embed.add_field(
        name=records[3]['record'],
        value=f"{get_flag(records[3]['username'])}{records[3]['username']} - "
              f"[{records[3]['adjusted']} WPM]"
              f"(https://data.typeracer.com/pit/result?id=|tr:{records[3]['username']}|{records[3]['race']}) - "
              f"{records[3]['date']}",
        inline=False
    )
    embed.add_field(
        name=records[4]['record'],
        value=f"{get_flag(records[4]['username'])}{records[4]['username']} - "
              f"[{records[4]['unlagged']} WPM]({records[4]['link']}) "
              f"({records[4]['lagged']} WPM Lagged) - {records[4]['date']}",
        inline=False
    )

    embed.add_field(
        name=records[5]['record'],
        value=f"{get_flag(records[5]['username'])}{records[5]['username']} - "
              f"[{records[5]['unlagged']} WPM]({records[5]['link']}) "
              f"({records[5]['lagged']} WPM Lagged) - {records[5]['date']}",
        inline=False
    )

    return embed


def club_400():
    i = 1
    scores_string = ""
    scores = races_300.get_races_unique_usernames()
    for score in scores:
        if score["wpm_adjusted"] < 400:
            break
        score["position"] = i
        score_string = get_score_string(score)
        scores_string += score_string + "\n"
        i += 1

    embed = Embed(
        title="˜”\*°• 400 WPM Club •°\*”˜",
        description=scores_string,
        color=colors.gold,
    )

    return embed


def club_300():
    i = 0
    scores_string = ""
    scores_string2 = ""
    scores = races_300.get_races_unique_usernames()
    scores = [score for score in scores if score["username"] not in exclude_300s]
    for score in scores[:25]:
        i += 1
        if score["wpm_adjusted"] >= 400:
            continue
        score["position"] = i
        score_string = get_score_string(score)
        scores_string += score_string + "\n"

    for score in scores[25:]:
        i += 1
        if score["wpm_adjusted"] >= 400:
            continue
        score["position"] = i
        score_string = get_score_string(score)
        scores_string2 += score_string + "\n"

    embed = Embed(
        title="300 WPM Club",
        description=scores_string,
        color=colors.gold,
    )

    embed2 = Embed(
        description=scores_string2,
        color=colors.gold,
    )

    return embed, embed2


def race_records():
    file = open("./data/records.json", "r")
    data = json.loads(file.read())
    records = data['races']

    embed = Embed(
        title="Race Records",
        color=colors.gold,
    )

    most_races = users.get_most("races", 3)
    most_daily_races = users.get_most_daily_races(3)
    most_characters = users.get_most("characters", 3)
    most_time = users.get_most("seconds", 3)
    most_races_str = ""
    most_daily_races_str = ""
    most_characters_str = ""
    most_time_str = ""

    for i, medal in enumerate(medals):
        user = most_races[i]
        username = user["username"]
        flag = get_flag(username)
        most_races_str += f"{medal} {flag}{user['username']} - {user['races']:,}\n"

        user = most_daily_races[i]
        username = user["username"]
        flag = get_flag(username)
        most_daily_races_str += (
            f"{medal} {flag}{user['username']} - "
            f"{user['daily_races']:,.2f} ({user['races']:,} races "
            f"over {user['days']:,} days)\n"
        )

        user = most_characters[i]
        username = user["username"]
        flag = get_flag(username)
        most_characters_str += f"{medal} {flag}{user['username']} - {user['characters']:,}\n"

        user = most_time[i]
        username = user["username"]
        flag = get_flag(username)
        most_time_str += (
            f"{medal} {flag}{user['username']} - "
            f"{utils.format_duration_short(user['seconds'])}\n"
        )

    embed.add_field(
        name="Most Races",
        value=most_races_str,
        inline=False,
    )

    embed.add_field(
        name="Highest Avg. Daily Races (Min. Account Age: 90 Days)",
        value=most_daily_races_str,
        inline=False,
    )

    embed.add_field(
        name="Most Characters Typed",
        value=most_characters_str,
        inline=False,
    )

    embed.add_field(
        name="Most In-Race Time",
        value=most_time_str,
        inline=False,
    )

    for record in records:
        record_string = (
            f"{get_flag(record['username'])}{record['username']} - "
            f"[{record['races']:,}]({record['link']}) - {record['date']}"
        )

        embed.add_field(
            name=record['record'],
            value=record_string,
            inline=False,
        )

    return embed


def point_records():
    file = open("./data/records.json", "r")
    data = json.loads(file.read())
    records = data['points']

    embed = Embed(
        title="Point Records",
        color=colors.gold,
    )

    most_points = users.get_most_total_points(3)
    most_daily_points = users.get_most_daily_points(3)
    most_points_str = ""
    most_daily_points_str = ""

    for i, medal in enumerate(medals):
        user = most_points[i]
        username = user["username"]
        flag = get_flag(username)
        most_points_str += f"{medal} {flag}{user['username']} - {user['points_total']:,.0f}\n"

        user = most_daily_points[i]
        username = user["username"]
        flag = get_flag(username)
        most_daily_points_str += (
            f"{medal} {flag}{user['username']} - "
            f"{user['daily_points']:,.0f} ({user['points_total']:,.0f} points "
            f"over {user['days']:,} days)\n"
        )

    embed.add_field(
        name="Most Points",
        value=most_points_str,
        inline=False,
    )

    embed.add_field(
        name="Highest Avg. Daily Points (Min. Account Age: 90 Days)",
        value=most_daily_points_str,
        inline=False,
    )

    for record in records:
        record_string = (
            f"{get_flag(record['username'])}{record['username']} - "
            f"[{record['points']:,}]({record['link']}) - {record['date']}"
        )

        embed.add_field(
            name=record['record'],
            value=record_string,
            inline=False,
        )

    return embed


def speedrun_records():
    file = open("./data/records.json", "r")
    data = json.loads(file.read())
    records = data['speedrun']

    embed = Embed(
        title="Speedrun Records",
        color=colors.gold,
    )

    for record in records:
        record_string = (
            f"{get_flag(record['username'])}{record['username']} - "
            f"[{record['time']}]({record['link']}) - {record['date']}"
        )

        embed.add_field(
            name=record['record'],
            value=record_string,
            inline=False,
        )

    return embed


def text_records():
    embed = Embed(
        title="Text Records",
        color=colors.gold,
    )

    text_bests = users.get_top_text_best(3)
    total_text_wpm = users.get_most("text_wpm_total", 3)
    most_texts = users.get_most("texts_typed", 3)
    max_quote = users.get_most_text_repeats(3)
    text_bests_str = ""
    total_text_wpm_str = ""
    most_texts_str = ""
    max_quote_str = ""

    for i, medal in enumerate(medals):
        user = text_bests[i]
        username = user["username"]
        flag = get_flag(username)
        text_bests_str += (
            f"{medal} {flag}{user['username']} - {user['text_best_average']:,.2f} WPM "
            f"({user['texts_typed']:,} texts typed)\n"
        )

        user = total_text_wpm[i]
        username = user["username"]
        flag = get_flag(username)
        total_text_wpm_str += (
            f"{medal} {flag}{user['username']} - {user['text_wpm_total']:,.0f} WPM "
            f"({user['texts_typed']:,} texts typed)\n"
        )

        user = most_texts[i]
        username = user["username"]
        flag = get_flag(username)
        most_texts_str += f"{medal} {flag}{user['username']} - {user['texts_typed']:,} texts\n"

        user = max_quote[i]
        username = user["username"]
        flag = get_flag(username)
        max_quote_str += (
            f"{medal} {flag}{user['username']} - [{user['max_quote_times']:,} times]"
            f"(https://typeracerdata.com/text.races?username=charlieog&text={user['max_quote_id']})\n"
        )

    embed.add_field(
        name="Text Best WPM (Min. 1,000 Texts Typed)",
        value=text_bests_str,
        inline=False,
    )

    embed.add_field(
        name="Total Text WPM",
        value=total_text_wpm_str,
        inline=False,
    )

    embed.add_field(
        name="Most Texts Typed",
        value=most_texts_str,
        inline=False,
    )

    embed.add_field(
        name="Most Times Typed a Single Quote",
        value=max_quote_str,
        inline=False,
    )

    return embed


def award_records():
    embed = Embed(
        title="Award Records",
        color=colors.gold,
    )

    most_awards = users.get_most_awards(3)
    most_awards_str = ""

    for i, medal in enumerate(medals):
        user = most_awards[i]
        username = user["username"]
        flag = get_flag(username)
        most_awards_str += (
            f"{medal} {flag}{user['username']} - {user['awards_total']:,} - "
            f":first_place: x{user['awards_first']:,} :second_place: x{user['awards_second']:,} "
            f":third_place: x{user['awards_third']:,}\n"
        )

    embed.add_field(
        name="Most Awards",
        value=most_awards_str,
        inline=False,
    )

    return embed


def get_score_string(score):
    username = score['username'].replace("_", "\\_")
    position = score['position']
    adjusted = score['wpm_adjusted']
    race_number = score['number']
    date = f"<t:{int(score['timestamp'])}:R>"
    rank = medals[position - 1] if position <= 3 else f"{position}."

    score_string = (
        f"{rank} {get_flag(username)}{username} - [{adjusted:.3f} WPM]"
        f"(https://data.typeracer.com/pit/result?id=|tr:{username}|{race_number}) - "
        f"{date}"
    )

    return score_string


def get_flag(username):
    country = countries[username.replace("\\", "")]
    if country is None:
        return ""

    return f":flag_{country}: "
