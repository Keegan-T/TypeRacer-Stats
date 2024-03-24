from discord.ext import commands
from config import prefix
from database.bot_users import get_user
from commands.basic.realspeed import get_params, run

graph_commands = ["rawgraph", "rawg", "rawadjustedgraph", "rag"]
info = {
    "name": "rawspeed",
    "aliases": ["raw"] + graph_commands,
    "description": "Displays raw speeds for a given user's race, subtracting correction time\n"
                   f"`{prefix}rawspeed [username] <-n> will return real speeds for n races ago`\n"
                   f"`{prefix}rawgraph` will add a graph of the race",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number",
    },
    "usages": [
        "rawspeed keegant 100000",
        "rawspeed keegant -1",
        "rawspeed https://data.typeracer.com/pit/result?id=|tr:keegant|1000000",
    ],
    "import": False,
    "multiverse": True,
}


class RawSpeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def rawspeed(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, race_number, universe = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, race_number, ctx.invoked_with.lower() in graph_commands, universe, raw=True)


async def setup(bot):
    await bot.add_cog(RawSpeed(bot))
