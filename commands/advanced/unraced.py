from discord import Embed
from discord.ext import commands
import urls
import utils
import errors
import colors
from database.bot_users import get_user
from commands.basic.stats import get_params
import database.users as users
import database.texts as texts
import random

info = {
    "name": "unraced",
    "aliases": ["ur"],
    "description": "Displays 5 unraced quotes for a user",
    "parameters": "[username]",
    "usages": ["unraced keegant"],
    "import": True,
}


class Unraced(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def unraced(self, ctx, *params):
        user = get_user(ctx)

        try:
            username = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username)


async def run(ctx, user, username):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    unraced = users.get_unraced_text_ids(username)
    text_count = texts.get_text_count()
    unraced_count = len(unraced)
    raced_percent = ((text_count - unraced_count) / text_count) * 100

    random.shuffle(unraced)
    unraced_string = ""

    for text in unraced[:5]:
        text_id = text["id"]
        unraced_string += (
            f"[Text #{text_id}]({urls.trdata_text(text_id)}) - [Ghost]({text['ghost']})\n"
            f'"{utils.truncate_clean(text["quote"], 500)}"\n\n'
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
    utils.add_profile(embed, stats)
    embed.set_footer(text=f"Raced {text_count - unraced_count:,}/{text_count:,} texts ({raced_percent:.2f}%)")

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Unraced(bot))
