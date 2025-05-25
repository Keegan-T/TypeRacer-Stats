from discord.ext import commands

from commands.advanced.day import get_args, run
from config import prefix
from database.bot.users import get_user
from utils import embeds

command = {
    "name": "week",
    "aliases": ["w", "lastweek", "yesterweek", "lw", "yw", "miniweek", "mw"],
    "description": "Displays a user's stats for a given week\n"
                   f"`{prefix}lastweek [username]` shows stats for the previous week\n"
                   f"`{prefix}miniweek [username]` will only show basic stats",
    "parameters": "[username] <date>",
    "defaults": {
        "date": "this week"
    },
    "usages": ["week keegant 2021-01-07"],
    "temporal": False,
}


class Week(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def week(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, date = result
        await run(ctx, user, username, date)


async def setup(bot):
    await bot.add_cog(Week(bot))
