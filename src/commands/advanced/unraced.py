import random

from discord import Embed
from discord.ext import commands

import database.texts as texts
import database.users as users
from commands.basic.stats import get_args
from database.bot_users import get_user
from utils import errors, colors, urls, strings, embeds

command = {
    "name": "unraced",
    "aliases": ["ur"],
    "description": "Displays 5 texts a user has not yet raced",
    "parameters": "[username]",
    "usages": ["unraced keegant"],
}


class Unraced(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def unraced(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)


async def run(ctx, user, username):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    unraced = users.get_unraced_text_ids(username, universe)
    text_count = texts.get_text_count(universe)
    unraced_count = len(unraced)
    raced_percent = ((text_count - unraced_count) / text_count) * 100

    random.shuffle(unraced)
    unraced_string = ""

    for text in unraced[:5]:
        text_id = text["id"]
        unraced_string += (
            f"[Text #{text_id}]({urls.trdata_text(text_id, universe)}) - [Ghost]({text['ghost']})\n"
            f'"{strings.truncate_clean(text["quote"], 500)}"\n\n'
        )

    color = user["colors"]["embed"]
    if unraced_count == 0:
        unraced_string = "User has raced all available texts!"
        color = colors.success

    embed = Embed(
        title=f"Unraced Texts - {unraced_count:,} left",
        description=unraced_string,
        color=color,
    )
    embeds.add_profile(embed, stats, universe)
    embed.set_footer(text=f"Raced {text_count - unraced_count:,}/{text_count:,} texts ({raced_percent:.2f}%)")
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Unraced(bot))
