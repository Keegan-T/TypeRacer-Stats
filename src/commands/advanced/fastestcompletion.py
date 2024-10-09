from discord import Embed
from discord.ext import commands

import database.races as races
import database.users as users
from commands.advanced.races import add_stats
from commands.locks import big_lock
from database.bot_users import get_user
from utils import errors, colors, strings, embeds

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
        if embeds.is_embed(result):
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

    if stats["races"] > 100_000:
        if big_lock.locked():
            return await ctx.send(embed=errors.large_query_in_progress())
        await big_lock.acquire()

    era_string = strings.get_era_string(user)
    if era_string:
        stats = await users.time_travel_stats(stats, user)

    if (category == "races" and number > stats["races"]) or number > stats["points"]:
        return await ctx.send(embed=no_milestone(category, universe), content=era_string)

    if category == "races":
        number = round(number)

    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = await races.get_races(
        username, columns=columns, universe=universe, start_date=user["start_date"], end_date=user["end_date"]
    )
    race_list.sort(key=lambda x: x[7])
    fastest = float("inf")
    race_range = []
    start_index = 0
    difference = float("inf")

    if category == "races":
        end_index = number
        while end_index < len(race_list):
            start_race = race_list[start_index]
            end_race = race_list[end_index - 1]
            difference = end_race[7] - start_race[7]
            if difference < fastest:
                fastest = difference
                race_range = [start_index, end_index]
            start_index += 1
            end_index += 1

        if difference < fastest:
            race_range = [start_index, end_index]

    else:
        total_points = 0
        single = False
        for end_index in range(0, len(race_list)):
            points = race_list[end_index][4]
            if points >= number:
                single = True
            total_points += points
            if total_points >= number:
                while total_points - race_list[start_index][4] >= number:
                    total_points -= race_list[start_index][4]
                    start_index += 1
                if race_list[end_index][7] - race_list[start_index][7] < fastest:
                    fastest = race_list[end_index][7] - race_list[start_index][7]
                    race_range = [start_index, end_index + 1]
            if single:
                race_range = [end_index, end_index + 1]
                break

    if not race_range:
        completion_races = race_list
        fastest = completion_races[-1][7] - completion_races[0][7]
    else:
        completion_races = race_list[race_range[0]:race_range[1]]
    start_time = completion_races[0][7]
    end_time = completion_races[-1][7]

    embed = Embed(
        title=f"Fastest Completion ({number:,} {category.title()})",
        description=f"{strings.format_duration_short(fastest, False)}",
        color=user["colors"]["embed"],
    )

    embeds.add_profile(embed, stats, universe)
    add_stats(embed, username, completion_races, start_time, end_time, universe=universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)

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
