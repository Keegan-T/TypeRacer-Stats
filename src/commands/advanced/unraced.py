import random

from discord.ext import commands

import database.texts as texts
import database.users as users
from database.bot_users import get_user
from utils import errors, colors, urls, strings
from utils.embeds import Page, Message, get_pages, is_embed

command = {
    "name": "unraced",
    "aliases": ["ur"],
    "description": "Displays 5 texts a user has not yet raced",
    "parameters": "[username] <category>",
    "defaults": {
        "category": "random"
    },
    "usages": ["unraced keegant"],
    "temporal": False,
}


class Unraced(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def unraced(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, category = result
        await run(ctx, user, username, category)


def get_args(user, args, info):
    params = f"username category:random|short|long|easy|hard"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, category):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    text_list = texts.get_texts(as_dictionary=True, include_disabled=False, universe=universe)
    unraced = users.get_unraced_texts(username, universe)
    text_count = texts.get_text_count(universe)
    unraced_count = len(unraced)
    completed = text_count - unraced_count

    if category == "random":
        random.shuffle(unraced)
    elif category in ["short", "long"]:
        unraced.sort(key=lambda x: len(x["quote"]), reverse=category == "long")
    elif category in ["easy", "hard"]:
        unraced.sort(key=lambda x: x["difficulty"], reverse=category == "hard")

    def formatter(text):
        text_id = text["id"]
        return (
            f"[Text #{text_id}]({urls.trdata_text(text_id, universe)}) - [Ghost]({text['ghost']})\n"
            f'"{strings.truncate_clean(text["quote"], 500)}"\n\n'
        )

    if unraced_count == 0:
        pages = Page(
            description="User has raced all available texts!",
            color=colors.success,
        )
    else:
        pages = get_pages(unraced, formatter, page_count=10, per_page=5)

    message = Message(
        ctx, user, pages,
        title=f"Unraced Texts - {unraced_count:,} left",
        footer=(
            f"Raced {completed:,}/{text_count:,} texts "
            f"({completed / text_count:.2%})"
        ),
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Unraced(bot))
