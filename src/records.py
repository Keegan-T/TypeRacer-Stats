import asyncio
from datetime import datetime

from discord import Embed

import database.main.club_races as club_races
import database.main.users as users
from config import records_channel
from database.main.records import get_records
from utils import colors, strings, urls
from utils.logging import log

sections = {
    "speed": lambda: speed_records(),
    "club": lambda: get_club_scores(),
    "races": lambda: race_records(),
    "points": lambda: point_records(),
    "speedrun": lambda: speedrun_records(),
    "text": lambda: text_records(),
    "awards": lambda: award_records(),
    "last_updated": lambda: Embed(
        title="Last Updated",
        description=strings.discord_timestamp(datetime.now().timestamp()),
        color=colors.gold,
    )
}
section_indexes = {
    "speed": 0,
    "club": [1, 2, 3],
    "races": 4,
    "points": 5,
    "speedrun": 6,
    "text": 7,
    "awards": 8,
    "last_updated": 9,
}
medals = [":first_place:", ":second_place:", ":third_place:"]
countries = {}


def set_countries():
    global countries
    countries = users.get_countries()


async def update_section(bot, section):
    set_countries()
    channel = bot.get_channel(records_channel)

    messages = [
        message async for message in channel.history(limit=None)
        if message.author == bot.user
    ]
    messages.reverse()

    indexes = section_indexes[section]
    if isinstance(indexes, int):
        indexes = [indexes]

    embeds = sections[section]()
    if asyncio.iscoroutine(embeds):
        embeds = await embeds
    if not isinstance(embeds, list) and not isinstance(embeds, tuple):
        embeds = [embeds]

    for i, index in enumerate(indexes):
        if index < len(messages):
            message = await channel.fetch_message(messages[index].id)
            await message.edit(embed=embeds[i])


async def update_all(bot):
    log("Updating TypeRacer Records")

    set_countries()
    channel = bot.get_channel(records_channel)

    messages = [
        message async for message in channel.history(limit=None)
        if message.author == bot.user
    ]
    messages.reverse()

    records = await get_all_records()

    # Mounting
    if not messages:
        for embed in records:
            await channel.send(embed=embed)

    # Updating
    else:
        for message, embed in zip(messages, records):
            await message.edit(embed=embed)

    log("Finished Updating Records")


async def get_all_records():
    embeds = [
        speed_records(),
        *get_club_scores(),
        race_records(),
        point_records(),
        speedrun_records(),
        await text_records(),
        award_records(),
        Embed(
            title="Last Updated",
            description=strings.discord_timestamp(datetime.now().timestamp()),
            color=colors.gold,
        ),
    ]

    return embeds


def speed_records():
    embed = Embed(title="Speed Records", color=colors.gold)
    add_database_records(embed, "speed", lambda record: f"{record} WPM")

    return embed


def format_club_scores(scores, filter):
    return [format_club_string(score) for score in scores if filter(score)]


def format_club_string(score):
    username = score["username"]
    position = score["position"]
    adjusted = score["wpm_adjusted"]
    race_number = score["number"]
    date = strings.discord_timestamp(score["timestamp"])
    rank = medals[position - 1] if position <= 3 else f"{position}."

    return (
        f"{rank} {get_flag(username)}{strings.escape_formatting(username)} - "
        f"[{adjusted:.3f} WPM]({urls.replay(username, race_number)}) - "
        f"{date}"
    )


def get_club_scores():
    top_scores = club_races.get_club_scores()

    embed_400 = Embed(
        title="˜”\\*°• 400 WPM Club •°\\*”˜",
        description="\n".join(
            format_club_scores(
                top_scores,
                lambda score: score["wpm_adjusted"] >= 400
            )
        ),
        color=colors.gold,
    )

    embed_300_1 = Embed(
        title="300 WPM Club",
        description="\n".join(
            format_club_scores(
                top_scores,
                lambda score: 300 <= score["wpm_adjusted"] < 400 and score["position"] <= 25
            )
        ),
        color=colors.gold,
    )

    embed_300_2 = Embed(
        description="\n".join(
            format_club_scores(
                top_scores,
                lambda score: 300 <= score["wpm_adjusted"] < 400 and score["position"] > 25
            )
        ),
        color=colors.gold,
    )

    return embed_400, embed_300_1, embed_300_2


def format_leaderboard(user_list, formatter):
    leaderboard = ""
    for i, user in enumerate(user_list):
        username = user["username"]
        flag = get_flag(username)
        leaderboard += f"{medals[i]} {flag}{strings.escape_formatting(username)} - {formatter(user)}\n"
    return leaderboard


def race_records():
    embed = Embed(title="Race Records", color=colors.gold)

    embed.add_field(
        name="Most Races",
        value=format_leaderboard(
            users.get_most("races", 3),
            lambda user: f"{user['races']:,}"
        ),
        inline=False,
    )

    embed.add_field(
        name="Highest Avg. Daily Races (Min. Account Age: 90 Days)",
        value=format_leaderboard(
            users.get_most_daily_races(3),
            lambda user: f"{user['daily_races']:,.2f} ({user['races']:,} races over {user['days']:,} days)"
        ),
        inline=False,
    )

    embed.add_field(
        name="Most Characters Typed",
        value=format_leaderboard(
            users.get_most("characters", 3),
            lambda user: f"{user['characters']:,}"
        ),
        inline=False,
    )

    embed.add_field(
        name="Most In-Race Time",
        value=format_leaderboard(
            users.get_most("seconds", 3),
            lambda user: strings.format_duration_short(user["seconds"])
        ),
        inline=False,
    )

    add_database_records(embed, "races", lambda record: f"{int(record):,}")

    return embed


def point_records():
    embed = Embed(title="Point Records", color=colors.gold)

    embed.add_field(
        name="Most Points",
        value=format_leaderboard(
            users.get_most_total_points(3),
            lambda user: f"{user['points_total']:,.0f}"
        ),
        inline=False,
    )

    embed.add_field(
        name="Highest Avg. Daily Points (Min. Account Age: 90 Days)",
        value=format_leaderboard(
            users.get_most_daily_points(3),
            lambda user: f"{user['daily_points']:,.0f} ({user['points_total']:,.0f} points over {user['days']:,} days)"
        ),
        inline=False,
    )

    add_database_records(embed, "points", lambda record: f"{int(record):,}")

    return embed


def speedrun_records():
    embed = Embed(title="Speedrun Records", color=colors.gold)
    add_database_records(embed, "speedrun", lambda record: record)

    return embed


async def text_records():
    embed = Embed(title="Text Records", color=colors.gold)

    from database.main.texts import get_text_count
    text_count = get_text_count()
    min_texts = int(text_count * 0.2)

    text_bests = users.get_top_text_best(3)
    total_text_wpm = users.get_most("text_wpm_total", 3)
    most_texts = users.get_most_texts_typed(20)
    text_repeats = users.get_most("text_repeat_times", 3)

    text_completion_str = ""
    for i, user in enumerate(most_texts):
        texts_typed = user["texts_typed"]
        if texts_typed < text_count:
            break
        min_repeats = user["min_repeats"]
        username = user["username"]
        repeat_string = f" ({min_repeats}x each)" if min_repeats > 1 else ""
        text_completion_str += f"{i + 1}. {get_flag(username)}{strings.escape_formatting(username)}{repeat_string}\n"

    embed.add_field(
        name=f"Text Best WPM (Min. {min_texts:,} Texts Typed)",
        value=format_leaderboard(
            text_bests,
            lambda user: f"{user['text_best_average']:,.2f} WPM ({user['texts_typed']:,} texts typed)"
        ),
        inline=False,
    )

    embed.add_field(
        name="Total Text WPM",
        value=format_leaderboard(
            total_text_wpm,
            lambda user: f"{user['text_wpm_total']:,.0f} WPM ({user['texts_typed']:,} texts typed)"
        ),
        inline=False,
    )

    embed.add_field(
        name=f"Text Completion Club ({text_count:,} Texts Typed)",
        value=text_completion_str,
        inline=False,
    )

    embed.add_field(
        name="Most Times Typed a Single Quote",
        value=format_leaderboard(
            text_repeats,
            lambda user: (
                f"[{user['text_repeat_times']:,} times]"
                f"({urls.trdata_text_races(user['username'], user['text_repeat_id'])})"
            )
        ),
        inline=False,
    )

    return embed


def award_records():
    embed = Embed(title="Award Records", color=colors.gold)

    most_awards = users.get_most_awards(3)

    embed.add_field(
        name="Most Awards",
        value=format_leaderboard(
            most_awards,
            lambda user: (
                f"{user['awards_total']:,} - "
                f":first_place: x{user['awards_first']:,} "
                f":second_place: x{user['awards_second']:,} "
                f":third_place: x{user['awards_third']:,}"
            )
        ),
        inline=False,
    )

    return embed


def get_flag(username):
    try:
        country = countries[username]
        return f":flag_{country}: " if country else ""
    except KeyError:
        return ""


def add_database_records(embed, category, formatter):
    records = get_records(category)

    for record in records:
        name, username, record, date, link = record
        flag = get_flag(username)
        embed.add_field(
            name=name,
            value=f"{flag}{strings.escape_formatting(username)} - "
                  f"[{formatter(record)}]({link}) - {date}",
            inline=False,
        )

    return embed
