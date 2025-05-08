from discord import Embed
from discord.ext import commands

import database.races as races
import database.users as users
from commands.advanced.races import get_stats_fields
from commands.locks import big_lock
from database import texts
from database.bot_users import get_user
from utils import errors, colors, strings, embeds
from utils.embeds import Message, Page, is_embed

categories = ["races", "points"]
command = {
    "name": "fastestcompletion",
    "aliases": ["fc"],
    "description": "Displays the shortest time a user has completed a number of race/points in",
    "parameters": "[username] <number> <category>",
    "defaults": {
        "number": 100,
        "category": "races",
    },
    "usages": [
        "fastestcompletion keegant 1000 races",
        "fastestcompletion keegant 10000 points",
    ],
}


class FastestCompletion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def fastestcompletion(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, number, category = result
        await run(ctx, user, username, number, category)


def get_args(user, args, info):
    params = f"username number:100 category:{'|'.join(categories)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, number, category):
    if number <= 1:
        return await ctx.send(embed=errors.greater_than(1))

    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    era_string = strings.get_era_string(user)
    if era_string:
        stats = await users.time_travel_stats(stats, user)

    if (category == "races" and number > stats["races"]) or number > stats["points"] + stats["points_retroactive"]:
        return await ctx.send(embed=no_milestone(category, universe), content=era_string)

    if stats["races"] > 100_000:
        if big_lock.locked():
            return await ctx.send(embed=errors.large_query_in_progress())
        await big_lock.acquire()

    text_list = texts.get_texts()
    text_lengths = {text["id"]: len(text["quote"]) for text in text_list}

    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = await races.get_races(
        username, columns=columns, universe=universe, start_date=user["start_date"], end_date=user["end_date"]
    )
    race_list.sort(key=lambda x: x[7])

    windows = []
    race_count = len(race_list)

    if category == "races":
        number = round(number)
        for start_index in range(race_count - number + 1):
            end_index = start_index + number
            start_race = race_list[start_index]
            start_time = start_race[7] - (text_lengths[start_race[0]] * 12) / start_race[2]
            end_race = race_list[end_index - 1]
            duration = end_race[7] - start_time
            windows.append([start_index, end_index, duration])

    else:
        start_index = 0
        total_points = 0
        for end_index in range(race_count):
            total_points += race_list[end_index][4]
            while total_points >= number:
                start_race = race_list[start_index]
                start_time = start_race[7] - (text_lengths[start_race[0]] * 12) / start_race[2]
                end_time = race_list[end_index][7]
                duration = end_time - start_time
                windows.append((start_index, end_index + 1, duration))
                total_points -= race_list[start_index][4]
                start_index += 1

    windows.sort(key=lambda x: x[2])

    top_windows = []
    used_ranges = []
    for start, end, duration in windows:
        overlap = False
        for s, e in used_ranges:
            if not (end <= s or start >= e):
                overlap = True
                break
        if not overlap:
            top_windows.append((start, end, duration))
            used_ranges.append((start, end))
            if len(top_windows) == 10:
                break

    fastest = top_windows[0]
    fastest_time = fastest[2]
    race_range = race_list[fastest[0]:fastest[1]]
    start_time = race_range[0]["timestamp"]
    end_time = race_range[-1]["timestamp"]
    fields, footer = get_stats_fields(
        username, race_range, start_time, end_time, universe="play"
    )

    description = ""
    for i in range(len(top_windows)):
        window = top_windows[i]
        duration = window[2]
        start_number = race_list[window[0]]["number"]
        end_number = race_list[window[1] - 1]["number"]
        description += (
            f"{i + 1}. **{strings.format_duration_short(duration, False)}** "
            f"(Races {start_number:,} - {end_number:,})\n"
        )

    pages = [
        Page(
            title=f"Fastest Completion ({number:,} {category.title()})",
            description=f"{strings.format_duration_short(fastest_time, False)}",
            fields=fields,
            footer=footer,
            button_name="Fastest",
        ),
        Page(
            f"Top 10 Fastest ({number:,} {category.title()})",
            description, button_name="Top 10",
        )
    ]

    message = Message(
        ctx, user, pages,
        profile=stats,
        universe=universe,
    )

    await message.send()

    if big_lock.locked():
        big_lock.release()


def no_milestone(category, universe):
    embed = Embed(
        title=f"Not Enough {category.title()}",
        description=f"This user has not achieved this many {category}",
        color=colors.error
    )
    embeds.add_universe(embed, universe)

    return embed


async def setup(bot):
    await bot.add_cog(FastestCompletion(bot))
