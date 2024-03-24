from discord import Embed
from discord.ext import commands
from src import colors, errors, utils
from database.bot_users import get_user
import database.users as users
import database.races as races
from commands.advanced.races import add_stats

types = ["races", "points"]
info = {
    "name": "fastestcompletion",
    "aliases": ["fc"],
    "description": "Displays the shortest time a user has completed a number of race/points in",
    "parameters": "[username] <number> <type>",
    "defaults": {
        "number": 100,
        "type": "races",
    },
    "usages": [
        "fastestcompletion keegant 1000 races",
        "fastestcompletion keegant 10000 points",
    ],
    "import": True,
}


class FastestCompletion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def fastestcompletion(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, number, kind = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, number, kind)


async def get_params(ctx, user, params):
    username = user["username"]
    number = 100
    kind = "races"

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        try:
            number = utils.parse_value_string(params[1])
        except ValueError:
            await ctx.send(embed=errors.invalid_number_format())
            raise

    if len(params) > 2:
        kind = utils.get_category(types, params[2])
        if not kind:
            await ctx.send(embed=errors.invalid_option("type", types))
            raise ValueError

    if number <= 1:
        await ctx.send(embed=errors.greater_than(1))
        raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), number, kind


async def run(ctx, user, username, number, kind):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    if (kind == "races" and number > stats["races"]) or number > stats["points"]:
        return await ctx.send(embed=no_milestone(kind))

    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = sorted(races.get_races(username, columns=columns), key=lambda x: x[7])
    fastest = float("inf")
    race_range = []
    start_index = 0
    difference = float("inf")

    if kind == "races":
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

    completion_races = race_list[race_range[0]:race_range[1]]
    start_time = completion_races[0][7]
    end_time = completion_races[-1][7]

    embed = Embed(
        title=f"Fastest Completion ({number:,} {kind.title()})",
        description=f"{utils.format_duration_short(fastest, False)}",
        color=user["colors"]["embed"],
    )

    utils.add_profile(embed, stats)
    add_stats(embed, username, completion_races, start_time, end_time)

    await ctx.send(embed=embed)


def no_milestone(kind):
    return Embed(
        title=f"Not Enough {kind.title()}",
        description=f"This user has not achieved this many {kind}",
        color=colors.error
    )


async def setup(bot):
    await bot.add_cog(FastestCompletion(bot))
