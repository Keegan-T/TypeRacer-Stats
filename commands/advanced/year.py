from discord.ext import commands
from config import prefix
from database.bot_users import get_user
from commands.advanced.day import get_params, run

info = {
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
    "import": True,
}


class Year(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def year(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, date = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, date)


async def setup(bot):
    await bot.add_cog(Year(bot))
