from discord import Embed
from discord.ext import commands

import database.main.texts as texts
from database.bot.users import get_user
from utils import urls

command = {
    "name": "disabledtexts",
    "aliases": ["dt"],
    "description": "Displays a list of texts that have been removed from text stats",
}


class DisabledTexts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def disabledtexts(self, ctx):
        user = get_user(ctx)

        await run(ctx, user)


async def run(ctx, user):
    disabled_text_ids = texts.get_disabled_text_ids()
    description = ", ".join([
        f"[{text_id}]({urls.trdata_text(text_id)})"
        for text_id in disabled_text_ids
    ])

    embed = Embed(
        title=f"Disabled Texts ({len(disabled_text_ids)})",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DisabledTexts(bot))
