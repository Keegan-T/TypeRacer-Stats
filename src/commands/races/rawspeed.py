from discord.ext import commands

from commands.races.realspeed import get_args, run
from config import prefix
from database.bot.users import get_user
from utils import embeds

command = {
    "name": "rawspeed",
    "aliases": ["raw"],
    "description": "Displays raw speeds for a given user's race, subtracting correction time\n"
                   f"`{prefix}rawspeed [username] <-n> will return raw speeds for n races ago`\n",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number",
    },
    "usages": [
        "rawspeed keegant 100000",
        "rawspeed keegant -1",
    ],
}


class RawSpeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def rawspeed(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command, ctx.channel.id)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, False, universe, raw=True)


async def setup(bot):
    await bot.add_cog(RawSpeed(bot))
