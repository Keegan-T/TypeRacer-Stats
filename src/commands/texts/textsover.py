from random import shuffle

from discord.ext import commands

import database.main.texts as texts
import database.main.users as users
from database.bot.users import get_user
from utils import errors, urls, strings
from utils.embeds import Page, Message, get_pages, is_embed

categories = ["wpm", "points", "times"]
sorts = ["wpm", "length", "times", "random"]
command = {
    "name": "textsover",
    "aliases": ["to"],
    "description": "Displays the number of texts a user has greater than or equal to a category threshold\n"
                   "Add `random` as a parameter to randomize the order in which texts are displayed",
    "parameters": f"[username] [threshold] <category:{'|'.join(categories)}> <sort:{'|'.join(sorts)}>",
    "defaults": {
        "category": "wpm",
        "sort": "wpm",
    },
    "usages": [
        "textsover joshua728 1000 points",
        "textsover charlieog 10000 times",
        "textsover keegant 200 wpm random",
        "textsover zak389 150 wpm length",
    ],
}


class TextsOver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textsover(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, threshold, category, sort = result
        await run(ctx, user, username, threshold, category, sort)


def get_args(user, args, info):
    params = f"username [number] category:{'|'.join(categories)} sort:{'|'.join(sorts)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, threshold, category, sort, over=True):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)
    if era_string or user["settings"]["text_pool"] != "all":
        stats = await users.filter_stats(stats, user)

    texts_typed = stats["texts_typed"]
    text_list = texts.get_texts(as_dictionary=True, universe=universe)

    if era_string:
        text_bests = await users.get_text_bests_time_travel(username, universe, user, race_stats=True, text_pool=user["settings"]["text_pool"])
    else:
        text_bests = users.get_text_bests(username, race_stats=True, universe=universe, text_pool=user["settings"]["text_pool"])

    if len(text_bests) == 0:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    text_bests_dict = {text["text_id"]: text for text in text_bests}
    final = []

    if over:
        race_list = users.get_texts_over(
            username, threshold, category, universe, start_date=user["start_date"], end_date=user["end_date"],
            text_pool=user["settings"]["text_pool"],
        )
    else:
        race_list = users.get_texts_under(
            username, threshold, category, universe, start_date=user["start_date"], end_date=user["end_date"],
            text_pool=user["settings"]["text_pool"],
        )

    for text in race_list:
        text_id = text["text_id"]
        text = {**text, **text_bests_dict[text_id]}
        final.append(text)
    race_list = final

    if sort == "random":
        shuffle(race_list)
        sort_title = " (Randomized)"
    elif sort == "length":
        race_list.sort(
            key=lambda x: len(text_list[x["text_id"]]["quote"]),
            reverse=ctx.invoked_with.lower() not in ["textsunder", "tu"]
        )
        sort_title = " (By Length)"
    elif sort == "times":
        race_list.sort(key=lambda x: x["times"], reverse=True)
        sort_title = " (By Times Typed)"
    else:
        race_list.sort(key=lambda x: x[category], reverse=True)
        sort_title = ""

    category_title = {"wpm": "WPM"}.get(category, category)
    race_count = len(race_list)
    header = (
        f"**{race_count:,}** of **{texts_typed:,}** texts are "
        f"{'above' if over else 'below'} {threshold:,} {category_title} "
        f"({race_count / texts_typed:.2%})\n\n"
    )

    if category == "points":
        category_title = f"Point{'s' if threshold != 1 else ''}"
    elif category == "times":
        category_title = f"Time{'s' if threshold != 1 else ''}"

    def formatter(race):
        text_id = race["text_id"]
        return (
            f"[#{text_id}]({urls.trdata_text(text_id, universe)}) - "
            f"[{race['wpm']:,.2f} WPM]({urls.replay(username, race['number'], universe)}) - "
            f"**{race['times']:,} time{'s' * (race['times'] != 1)}** - "
            f"{len(text_list[text_id]["quote"]):,} chars - "
            f"[Ghost]({text_list[text_id]['ghost']})\n"
            f'"{strings.truncate_clean(text_list[text_id]["quote"], 60)}"\n\n'
        )

    title = (
        f"Texts {'Over' if over else 'Under'} {threshold:,} "
        f"{category_title}{sort_title}"
    )

    if race_list:
        pages = get_pages(race_list, formatter, page_count=10, per_page=10)
    else:
        pages = Page()

    message = Message(
        ctx, user, pages,
        title=title,
        header=header,
        profile=stats,
        universe=universe,
        text_pool=user["settings"]["text_pool"],
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(TextsOver(bot))
