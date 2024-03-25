from discord.ext import commands
from database.bot_users import get_user
from commands.advanced.raceline import get_params, run
import commands.locks as locks
from commands.locks import line_lock
from commands.basic.realspeedaverage import command_in_use

info = {
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
    "import": True,
}


class PointLine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def pointline(self, ctx, *params):
        if locks.line_lock.locked():
            return await ctx.send(embed=command_in_use())

        async with line_lock:
            user = get_user(ctx)

            try:
                usernames, start_date, end_date = await get_params(ctx, user, params, info)
            except ValueError:
                return

            await run(ctx, user, usernames, start_date, end_date, True)


async def setup(bot):
    await bot.add_cog(PointLine(bot))
