from discord.ext import commands

from commands.races.day import get_args, run
from config import prefix
from database.bot.users import get_user
from utils import embeds

command = {
    "name": "year",
    "aliases": ["y", "lastyear", "yesteryear", "ly", "yy", "miniyear", "my"],
    "description": "Displays a user's stats for a given year\n"
                   f"`{prefix}lastyear [username]` shows stats for the previous year\n"
                   f"`{prefix}miniyear [username]` will only show basic stats",
    "parameters": "[username] <year>",
    "defaults": {
        "date": "this year"
    },
    "usages": ["year keegant 2021"],
    "temporal": False,
}


class Year(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def year(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, date = result
        await run(ctx, user, username, date)


async def setup(bot):
    await bot.add_cog(Year(bot))
