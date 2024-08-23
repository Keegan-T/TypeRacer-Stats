from discord import Embed
from discord.ext import commands

import database.races as races
import database.texts as texts
import database.users as users
from api.texts import get_text_list
from api.universes import get_universe_list
from database.bot_users import get_user, update_universe
from utils import colors
from utils.logging import log

command = {
    "name": "setuniverse",
    "aliases": ["su"],
    "description": "Sets the TypeRacer universe for your account to retrieve stats from\n"
                   "Only some commands will work in the multiverse (none that require import)",
    "parameters": "<universe>",
    "defaults": {
        "universe": "play",
    },
    "usages": ["setuniverse dictionary"],
}


class SetUniverse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def setuniverse(self, ctx, *args):
        user = get_user(ctx)

        universe = "play"
        if args:
            universe = args[0].lower()

        universes = get_universe_list()
        if universe not in universes:
            return await ctx.send(embed=unknown_universe())

        await run(ctx, user, universe)


async def run(ctx, user, universe):
    if not texts.universe_exists(universe):
        create_universe(universe)

    update_universe(ctx.author.id, universe)

    embed = Embed(
        title="Universe Updated",
        description=f"Set universe to [{universe}](https://play.typeracer.com/?universe={universe})",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


def create_universe(universe):
    log(f"Creating universe: {universe}")

    users.create_table(universe)
    races.create_table(universe)

    texts.create_table(universe)
    text_list = get_text_list(universe)
    texts.add_texts(text_list, universe)

    log("Finished creating universe")


def unknown_universe():
    return Embed(
        title="Unknown Universe",
        description="Failed to recognize this universe",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(SetUniverse(bot))
