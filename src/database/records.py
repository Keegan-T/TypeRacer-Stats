import json
from datetime import datetime

from discord import Embed

import database.races_300 as races_300
import database.users as users
from config import records_channel
from utils import colors, strings
from utils.logging import send_message

medals = [":first_place:", ":second_place:", ":third_place:"]
countries = {}


def set_countries():
    global countries
    countries = users.get_countries()


async def update(bot):
    await send_message("Updating TypeRacer Records")
    channel = bot.get_channel(records_channel)
    message_history = channel.history(limit=None)
    messages = []
    async for message in message_history:
        if message.author == bot.user:
            messages.append(message.id)

    messages.reverse()

    records = await get_records()

    # Mounting
    if not messages:
        for embed in records:
            await channel.send(embed=embed)

    # Updating
    else:
        record_list = iter(records)
        for message_id in messages:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=next(record_list))

    await send_message("Finished Updating Records")


async def update_300_club(bot):
    set_countries()
    channel = bot.get_channel(records_channel)
    message_history = channel.history(limit=None)
    messages = []
    async for message in message_history:
        if message.author == bot.user:
            messages.append(message.id)

    messages.reverse()

    club_400, club_300_1, club_300_2 = get_club_scores()

    records = [
        club_400,
        club_300_1,
        club_300_2,
    ]

    if not messages:
        return

    else:
        record_list = iter(records)
        for message_id in messages[1:4]:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=next(record_list))


async def get_records():
    date = datetime.now()
    set_countries()

    last_updated = Embed(
        title="Last Updated",
        description=strings.discord_timestamp(date.timestamp()),
        color=colors.gold,
    )

    club_400, club_300_1, club_300_2 = get_club_scores()

    embeds = [
        speed_records(),
        club_400,
        club_300_1,
        club_300_2,
        race_records(),
        point_records(),
        speedrun_records(),
        await text_records(),
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
              f"[{records[0]['adjusted']} WPM]"
              f"(https://data.typeracer.com/pit/result?id=|tr:{records[0]['username']}|{records[0]['race']}) "
              f"({records[0]['lagged']} WPM Lagged) - {records[0]['date']}",
        inline=False
    )

    embed.add_field(
        name=records[1]['record'],
        value=f"{get_flag(records[1]['username'])}{records[1]['username']} - "
              f"[{records[1]['unlagged']} WPM]"
              f"(https://data.typeracer.com/pit/result?id=|tr:{records[1]['username']}|{records[1]['race']}) "
              f"({records[1]['lagged']} WPM Lagged) - {records[1]['date']}",
        inline=False
    )

    embed.add_field(
        name=records[2]['record'],
        value=f"{get_flag(records[2]['username'])}{records[2]['username']} - "
              f"[{records[2]['adjusted']} WPM]"
              f"(https://data.typeracer.com/pit/result?id=|tr:{records[2]['username']}|{records[2]['race']}) - "
              f"{records[2]['date']}",
        inline=False
    )
    embed.add_field(
        name=records[3]['record'],
        value=f"{get_flag(records[3]['username'])}{records[3]['username']} - "
              f"[{records[3]['unlagged']} WPM]({records[3]['link']}) "
              f"({records[3]['lagged']} WPM Lagged) - {records[3]['date']}",
        inline=False
    )

    embed.add_field(
        name=records[4]['record'],
        value=f"{get_flag(records[4]['username'])}{records[4]['username']} - "
              f"[{records[4]['unlagged']} WPM]({records[4]['link']}) "
              f"({records[4]['lagged']} WPM Lagged) - {records[4]['date']}",
        inline=False
    )

    return embed


def get_club_scores():
    from database.alts import get_alts

    i = 1
    scores = races_300.get_races_unique_usernames()
    top_scores = []
    alts = get_alts()
    for score in scores:
        username = score["username"]
        if username in alts:
            existing_score = next((score for score in top_scores if score["username"] in alts[username]), None)
        else:
            existing_score = next((score for score in top_scores if score["username"] == username), None)
        if not existing_score:
            score["position"] = i
            top_scores.append(score)
            i += 1

    score_string_400 = ""
    score_string_300_1 = ""
    score_string_300_2 = ""
    for score in top_scores:
        score_string = get_score_string(score)
        if score["wpm_adjusted"] >= 400:
            score_string_400 += score_string + "\n"
        elif score["position"] <= 25:
            score_string_300_1 += score_string + "\n"
        else:
            score_string_300_2 += score_string + "\n"

    embed_400 = Embed(
        title="˜”\*°• 400 WPM Club •°\*”˜",
        description=score_string_400,
        color=colors.gold,
    )

    embed_300_1 = Embed(
        title="300 WPM Club",
        description=score_string_300_1,
        color=colors.gold,
    )

    embed_300_2 = Embed(
        description=score_string_300_2,
        color=colors.gold,
    )

    return embed_400, embed_300_1, embed_300_2


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
            f"{strings.format_duration_short(user['seconds'])}\n"
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


async def text_records():
    embed = Embed(
        title="Text Records",
        color=colors.gold,
    )

    from database.texts import get_text_count
    text_count = get_text_count()
    min_texts = int(text_count * 0.2)
    text_bests = users.get_top_text_best(3)
    total_text_wpm = users.get_most("text_wpm_total", 3)
    most_texts = users.get_most("texts_typed", 20)
    max_quote = await users.get_most_text_repeats(3)
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

        user = max_quote[i]
        username = user["username"]
        flag = get_flag(username)
        max_quote_str += (
            f"{medal} {flag}{user['username']} - [{user['max_quote_times']:,} times]"
            f"(https://typeracerdata.com/text.races?username=charlieog&text={user['max_quote_id']})\n"
        )

    max_texts_typed = most_texts[0]["texts_typed"]
    for i in range(len(most_texts)):
        user = most_texts[i]
        texts_typed = user["texts_typed"]
        if texts_typed < max_texts_typed:
            break
        user = most_texts[i]
        username = user["username"]
        flag = get_flag(username)
        most_texts_str += f"{i + 1}. {flag}{user['username']}\n"

    embed.add_field(
        name=f"Text Best WPM (Min. {min_texts:,} Texts Typed)",
        value=text_bests_str,
        inline=False,
    )

    embed.add_field(
        name="Total Text WPM",
        value=total_text_wpm_str,
        inline=False,
    )

    embed.add_field(
        name=f"Text Completion Club ({max_texts_typed:,} Texts Typed)",
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
    try:
        country = countries[username.replace("\\", "")]
        if country is None:
            return ""
    except KeyError:
        return ""

    return f":flag_{country}: "
