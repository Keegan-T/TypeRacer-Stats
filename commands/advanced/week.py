from discord.ext import commands
from config import prefix
from database.bot_users import get_user
from commands.advanced.day import get_params, run

info = {
    "name": "week",
    "aliases": ["w", "lastweek", "yesterweek", "lw", "yw"],
    "description": "Displays a user's stats for a given week\n"
                   f"`{prefix}lastweek [username]` shows stats for the previous week",
    "parameters": "[username] <date>",
    "defaults": {
        "date": "this week"
    },
    "usages": ["week keegant 2021-01-07"],
    "import": True,
}

class Week(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def week(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, date = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, date)


async def setup(bot):
    await bot.add_cog(Week(bot))
