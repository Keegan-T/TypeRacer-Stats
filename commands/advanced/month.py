from discord.ext import commands
from config import prefix
from database.bot_users import get_user
from commands.advanced.day import get_params, run

info = {
    "name": "month",
    "aliases": ["m", "lastmonth", "yestermonth", "lm", "ym", "minimonth", "mm"],
    "description": "Displays a user's stats for a given month\n"
                   f"`{prefix}lastmonth [username]` shows stats for the previous month\n"
                   f"`{prefix}minimonth [username]` will only show basic stats",
    "parameters": "[username] <month>",
    "defaults": {
        "date": "this month"
    },
    "usages": ["month keegant 2021-01"],
    "import": True,
}


class Month(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def month(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, date = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, date)


async def setup(bot):
    await bot.add_cog(Month(bot))
