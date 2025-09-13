from discord.ext import commands

import commands.locks as locks
from commands.graphs.raceline import get_args, run
from database.bot.users import get_user
from utils import embeds, dates
from utils.errors import command_in_use

command = {
    "name": "pointline",
    "aliases": ["pl"],
    "description": "Displays a graph of user's points over time",
    "parameters": "[username] <username_2> ... <username_10> <start_date> <end_date>",
    "usages": [
        "pointline keegant",
        "pointline keegant 2022-04-20",
        "pointline keegant 4/20/22 1/1/24",
        "pointline keegant mark40511 charlieog wordracer888 deroche1",
    ],
}


class PointLine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def pointline(self, ctx, *args):
        if locks.line_lock.locked():
            return await ctx.send(embed=command_in_use())

        async with locks.line_lock:
            user = get_user(ctx)
            args, user = dates.set_command_date_range(args, user)

            result = get_args(user, args, command)
            if embeds.is_embed(result):
                return await ctx.send(embed=result)

            await run(ctx, user, result, column="points")


async def setup(bot):
    await bot.add_cog(PointLine(bot))
