from discord.ext import commands
from config import prefix
from database.bot_users import get_user
from commands.basic.realspeed import get_params
from commands.advanced.text import run

info = {
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
        "racetext https://data.typeracer.com/pit/result?id=|tr:keegant|1000000",
    ],
    "import": True,
}


class RaceText(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def racetext(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, race_number, _ = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, race_number=race_number)


async def setup(bot):
    await bot.add_cog(RaceText(bot))
