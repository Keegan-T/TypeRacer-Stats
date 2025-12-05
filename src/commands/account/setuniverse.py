import requests
from discord import Embed
from discord.ext import commands

import database.main.texts as texts
from api.texts import get_text_list
from database.bot.users import get_user, update_universe
from database.main.users import get_universe_list
from utils import colors, strings

command = {
    "name": "setuniverse",
    "aliases": ["su"],
    "description": "Sets the TypeRacer universe for your account to retrieve stats from\n",
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
            url = f"https://play.typeracer.com/?universe={strings.escape_url(universe)}"
            response = requests.get(url)
            if response.status_code == 404:
                return await ctx.send(embed=unknown_universe())
            else:
                await ctx.send(embed=fetching_texts(user))
                text_list = get_text_list(universe)
                if text_list:
                    texts.add_texts(text_list, universe)

        await run(ctx, user, universe)


async def run(ctx, user, universe):
    update_universe(ctx.author.id, universe)

    embed = Embed(
        title="Universe Updated",
        description=f"Set universe to [{universe}](https://play.typeracer.com/?universe={universe})",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


def fetching_texts(user):
    return Embed(
        title="New Universe",
        description="Fetching universe texts",
        color=user["colors"]["embed"],
    )


def unknown_universe():
    return Embed(
        title="Unknown Universe",
        description="Failed to recognize this universe",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(SetUniverse(bot))
