import json

import requests
from discord import Embed
from discord.ext import commands

from database.bot_users import get_user
from utils import errors, colors

command = {
    "name": "define",
    "aliases": ["def"],
    "description": "Displays the definition(s) of a word",
    "parameters": "[word]",
    "usages": ["define typing"],
}


class Define(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def define(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return await ctx.send(embed=errors.missing_argument(command))

        await run(ctx, user, args[0])


async def run(ctx, user, word):
    response = requests.get("https://api.dictionaryapi.dev/api/v2/entries/en/" + word)
    data = json.loads(response.text)
    if "title" in data:
        return await ctx.send(embed=unknown_word())

    definitions = data[0]["meanings"]

    description = ""
    for group in definitions:
        part = group["partOfSpeech"].title()
        description += f"**{part}**\n"
        for definition in group["definitions"]:
            description += "\\- " + definition["definition"] + "\n"
        description += "\n"

    embed = Embed(
        title=word.title() + " - Definition",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Define(bot))


def unknown_word():
    return Embed(
        title="Unknown Word",
        description="Sorry, I don't know this word",
        color=colors.error,
    )
