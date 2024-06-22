from discord.ext import commands
from database.bot_users import get_user
from commands.advanced.raceline import get_args, run
import commands.locks as locks
from commands.locks import line_lock
from commands.basic.realspeedaverage import command_in_use
import utils

command = {
    "name": "pointline",
    "aliases": ["pl"],
    "description": "Displays a graph of user's points over time",
    "parameters": "<date> [username] <username_2> ... <username_10> <date>",
    "usages": [
        "pointline keegant",
        "pointline 2022-04-20 keegant",
        "pointline 4/20/22 keegant 1/1/24",
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

        async with line_lock:
            user = get_user(ctx)

            result = get_args(user, args, command)
            if utils.is_embed(result):
                return await ctx.send(embed=result)

            usernames, start_date, end_date = result
            await run(ctx, user, usernames, start_date, end_date, column="points")


async def setup(bot):
    await bot.add_cog(PointLine(bot))
