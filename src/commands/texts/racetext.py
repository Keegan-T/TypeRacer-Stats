from discord.ext import commands

from commands.texts.text import run
from commands.races.realspeed import get_args
from config import prefix
from database.bot.users import get_user
from utils import embeds

command = {
    "name": "racetext",
    "aliases": ["rt", "racetextgraph", "rtg"],
    "description": "Displays a user's stats about the text of a specific race\n"
                   f"`{prefix}racetextgraph [username] <-n>` will display the text for n races ago\n"
                   f"`{prefix}racetextgraph` will add an improvement graph",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number",
    },
    "usages": [
        "racetext keegant 100000",
        "racetext keegant -1",
    ],
}


class RaceText(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def racetext(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command, ctx.channel.id)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, _ = result
        await run(ctx, user, username, race_number=race_number)


async def setup(bot):
    await bot.add_cog(RaceText(bot))
