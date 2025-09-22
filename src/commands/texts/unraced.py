import random

from discord import File
from discord.ext import commands

import database.main.texts as texts
import database.main.users as users
from config import prefix
from database.bot.users import get_user
from database.main.races import maintrack_text_pool
from utils import errors, colors, urls, strings, files
from utils.embeds import Page, Message, get_pages, is_embed

command = {
    "name": "unraced",
    "aliases": ["ur"],
    "description": "Displays 5 texts a user has not yet raced\n"
                   f"`{prefix}unraced [username] export` will attach a file with links to all unraced texts",
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
        if category == "export":
            return await export(ctx, user, username)

        await run(ctx, user, username, category)


def get_args(user, args, info):
    params = f"username category:random|short|long|easy|hard|export"

    return strings.parse_command(user, params, args, info)


async def export(ctx, user, username):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    unraced = users.get_unraced_texts(username, universe)
    links = "\n".join(text["ghost"] for text in unraced)
    file_name = f"{username}_unraced.txt"
    with open(file_name, "w") as file:
        file.write(links)

    await ctx.send(file=File(file_name))
    files.remove_file(file_name)


async def run(ctx, user, username, category):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    unraced = users.get_unraced_texts(username, universe, text_pool=user["settings"]["text_pool"])
    text_count = texts.get_text_count(universe)
    if user["settings"]["text_pool"] == "maintrack":
        text_count = len(maintrack_text_pool)
    unraced_count = len(unraced)
    completed = text_count - unraced_count

    if category == "random":
        random.shuffle(unraced)
    elif category in ["short", "long"]:
        unraced.sort(key=lambda x: len(x["quote"]), reverse=category == "long")
    elif category in ["easy", "hard"]:
        unraced.sort(key=lambda x: x["difficulty"], reverse=category == "hard")

    def formatter(text):
        text_id = text["text_id"]
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
        time_travel=False,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Unraced(bot))
