from discord import Embed
from discord.ext import commands

import utils
import errors
import colors
from database.bot_users import get_user
import database.users as users
import database.races as races

command = {
    "name": "bestaverages",
    "aliases": ["ba"],
    "description": "Displays a user's top 10 best average of n races\n"
                   "Averages will not contain overlapping races",
    "parameters": "[username] <n>",
    "defaults": {
        "n": 10,
    },
    "usages": ["bestaverages keegant 10"],
}


class BestAverages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def bestaverages(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, n = result
        await run(ctx, user, username, n)


def get_args(user, args, info):
    params = "username int:10"

    return utils.parse_command(user, params, args, info)


async def run(ctx, user, username, n):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    if n < 1:
        return await ctx.send(embed=errors.greater_than(0))

    if n > stats["races"]:
        return await ctx.send(embed=not_enough_races())

    race_list = await races.get_races(username, columns=["wpm", "number", "timestamp"])
    race_list.sort(key=lambda x: x[2])
    description = ""

    count = 10
    averages = [sum([race[0] for race in race_list[:n]])]
    start_index = 0
    end_index = n
    while end_index < len(race_list):
        average = averages[start_index]
        average -= race_list[start_index][0]
        average += race_list[end_index][0]
        averages.append(average)
        start_index += 1
        end_index += 1

    for i in range(count):
        best = max(averages)
        if best == 0:
            break
        best_index = averages.index(best)
        for j in range(-n + 1, n):
            target_index = best_index + j
            if 0 <= target_index < len(averages):
                averages[target_index] = 0

        start_number = race_list[best_index][1]
        end_number = race_list[best_index + n - 1][1]
        description += f"**{best / n:,.2f} WPM:** Races #{start_number:,} - {end_number:,}\n"

    embed = Embed(
        title=f"Best Last {n:,} Averages",
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)


def not_enough_races():
    return Embed(
        title="Not Enough Races",
        description="User has not completed this many races",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(BestAverages(bot))
