from discord.ext import commands

from commands.advanced.racesover import get_args, run
from database.bot_users import get_user
from utils import embeds

command = {
    "name": "racesunder",
    "aliases": ["ru"],
    "description": "Displays the number of races a user has less than a category threshold",
    "parameters": "[username] [threshold] <category>",
    "defaults": {
        "category": "wpm",
    },
    "usages": [
        "racesunder keegant 100 wpm",
        "racesunder keegant 50 points",
    ],
}


class RacesUnder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def racesunder(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, threshold, category = result
        await run(ctx, user, username, threshold, category, over=False)


async def setup(bot):
    await bot.add_cog(RacesUnder(bot))
