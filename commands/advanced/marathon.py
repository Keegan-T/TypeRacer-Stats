from discord import Embed
from discord.ext import commands
from src import colors, errors, utils
from database.bot_users import get_user
import database.users as users
import database.races as races
from commands.advanced.races import add_stats

types = ["races", "points"]
info = {
    "name": "marathon",
    "aliases": ["mt", "42"],
    "description": "Displays the maximum amount of races/points a user completed in a timeframe\n"
                   "Time can be given as seconds, or a duration string (1d 12h 30m 15s)",
    "parameters": "[username] <type> <time>",
    "defaults": {
        "type": "races",
        "time": "24 hours",
    },
    "usages": [
        "marathon keegant",
        "marathon keegant races",
        "marathon keegant 12h",
        "marathon keegant points 1h 30m",
    ],
    "import": True,
}


class Marathon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def marathon(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, kind, seconds = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, kind, seconds)


async def get_params(ctx, user, params):
    username = user["username"]
    kind = "races"
    seconds = 86400

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        kind = utils.get_category(types, params[1])
        if not kind:
            await ctx.send(embed=errors.invalid_option("type", types))
            raise ValueError

    if len(params) > 2:
        try:
            seconds = utils.parse_duration_string(" ".join(params[2:]))
        except ValueError:
            await ctx.send(embed=errors.invalid_duration_format())
            raise

    if seconds <= 0:
        await ctx.send(embed=invalid_duration())
        raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), kind, seconds


async def run(ctx, user, username, kind, seconds):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = sorted(races.get_races(username, columns=columns), key=lambda x: x[7])
    marathon = 0
    race_range = []
    start_index = 0
    end_index = 0
    current = -1

    if kind == "races":
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
        title=f"Best {kind[:-1].title()} Marathon "
              f"({utils.format_duration_short(seconds, False)} period)",
        color=user["colors"]["embed"],
    )

    utils.add_profile(embed, stats)

    add_stats(embed, username, marathon_races, start_time, end_time)

    await ctx.send(embed=embed)


def invalid_duration():
    return Embed(
        title="Invalid Duration",
        description="Duration must be greater than 0 seconds",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Marathon(bot))
