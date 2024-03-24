from discord.ext import commands
from database.bot_users import get_user
from commands.advanced.racesover import get_params, run

info = {
    "name": "racesunder",
    "aliases": ["ru"],
    "description": "Displays the number of races a user has less than a category threshold",
    "parameters": "[username] [threshold] [category]",
    "usages": [
        "racesunder keegant 100 wpm",
        "racesunder keegant 50 points",
    ],
    "import": True,
}


class RacesUnder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def racesunder(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, threshold, category = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, threshold, category, False)


async def setup(bot):
    await bot.add_cog(RacesUnder(bot))
