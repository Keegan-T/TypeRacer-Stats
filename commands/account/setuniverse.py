from discord import Embed
from discord.ext import commands

import colors
from database.bot_users import get_user, update_universe
from api.universes import get_universe_list

info = {
    "name": "setuniverse",
    "aliases": ["su"],
    "description": "Sets the TypeRacer universe for your account to retrieve stats from\n"
                   "Only some commands will work in the multiverse (none that require import)",
    "parameters": "<universe>",
    "defaults": {
        "universe": "play",
    },
    "usages": ["setuniverse dictionary"],
    "import": False,
}

class SetUniverse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def setuniverse(self, ctx, *params):
        user = get_user(ctx)

        universe = "play"
        if params:
            universe = params[0].lower()

        universes = get_universe_list()
        if universe not in universes:
            return await ctx.send(embed=unknown_universe())

        await run(ctx, user, universe)

async def run(ctx, user, universe):
    update_universe(ctx.author.id, universe)

    embed = Embed(
        title="Universe Updated",
        description=f"Set universe to [{universe}](https://play.typeracer.com/?universe={universe})",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)

def unknown_universe():
    return Embed(
        title="Unknown Universe",
        description="Failed to recognize this universe",
        color=colors.error,
    )

async def setup(bot):
    await bot.add_cog(SetUniverse(bot))