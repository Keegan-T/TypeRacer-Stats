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
    "name": "marathon",
    "aliases": ["42"],
    "description": "Displays the maximum amount of races/points a user completed in a timeframe\n"
                   "Time can be given as seconds, or a duration string (1d 12h 30m 15s)",
    "parameters": "[username] <category> <time>",
    "defaults": {
        "category": "races",
        "time": "24 hours",
    },
    "usages": [
        "marathon keegant",
        "marathon keegant races",
        "marathon keegant points 1h30m",
    ],
}


class Marathon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def marathon(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        if big_lock.locked():
            return await ctx.send(embed=errors.large_query_in_progress())

        username, category, seconds = result
        await run(ctx, user, username, category, seconds)


def get_args(user, args, info):
    params = f"username category:{'|'.join(categories)} duration:86400"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, category, seconds):
    if seconds <= 0:
        return await ctx.send(embed=invalid_time())

    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    if stats["races"] > 100_000:
        await big_lock.acquire()

    era_string = strings.get_era_string(user)

    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = await races.get_races(
        username, columns=columns, universe=universe,
        start_date=user["start_date"], end_date=user["end_date"]
    )
    if not race_list:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    race_list.sort(key=lambda x: x[7])
    marathon = 0
    race_range = []
    start_index = 0
    end_index = 0
    current = -1

    if category == "races":
        # I deem this the "inchworm" technique
        while end_index < len(race_list):
            start_race = race_list[start_index]
            end_race = race_list[end_index]
            if end_race[7] - start_race[7] < seconds:
                current = end_index - start_index + 1
                end_index += 1
                if current > marathon:
                    marathon = current
                    race_range = [start_index, end_index]
            else:
                start_index += 1

    else:
        total_points = 0

        while end_index < len(race_list):
            start_race = race_list[start_index]
            end_race = race_list[end_index]
            if end_race[7] - start_race[7] < seconds:
                total_points += end_race[4]
                current = total_points
                end_index += 1
                if current > marathon:
                    marathon = current
                    race_range = [start_index, end_index]
            else:
                total_points -= start_race[4]
                start_index += 1

    if current > marathon:
        race_range = [start_index, end_index]

    marathon_races = race_list[race_range[0]:race_range[1]]
    start_time = marathon_races[0][7]
    end_time = marathon_races[-1][7]

    embed = Embed(
        title=f"Best {category[:-1].title()} Marathon "
              f"({strings.format_duration_short(seconds, False)} period)",
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    add_stats(embed, username, marathon_races, start_time, end_time, universe=universe)

    await ctx.send(embed=embed, content=era_string)

    if big_lock.locked():
        big_lock.release()


def invalid_time():
    return Embed(
        title="Invalid Time",
        description="Time must be greater than 0 seconds",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Marathon(bot))
