from random import shuffle

from discord import Embed
from discord.ext import commands

import database.texts as texts
import database.users as users
from database.bot_users import get_user
from utils import errors, urls, strings, embeds

categories = ["wpm", "points", "times"]
command = {
    "name": "textsover",
    "aliases": ["to"],
    "description": "Displays the number of texts a user has greater than or equal to a category threshold\n"
                   "Add `random` as a parameter to randomize the order in which texts are displayed",
    "parameters": "[username] [threshold] <category>",
    "defaults": {
        "category": "wpm",
    },
    "usages": [
        "textsover joshua728 1000 points",
        "textsover charlieog 5000 times",
        "textsover keegant 200 wpm random",
    ],
}


class TextsOver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textsover(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, threshold, category = result
        random = args[-1] in ["random", "rand", "r"]
        await run(ctx, user, username, threshold, category, random=random)


def get_args(user, args, info):
    params = f"username [number] category:{'|'.join(categories)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, threshold, category, over=True, random=False):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    texts_typed = stats["texts_typed"]
    text_list = texts.get_texts(as_dictionary=True, universe=universe)

    text_bests = users.get_text_bests(username, race_stats=True, universe=universe)
    text_bests_dict = {}
    for text in text_bests:
        text_bests_dict[text["text_id"]] = text

    final = []

    if over:
        race_list = users.get_texts_over(username, threshold, category, universe)
    else:
        race_list = users.get_texts_under(username, threshold, category, universe)

    for text in race_list:
        text_id = text["text_id"]
        text = {**text, **text_bests_dict[text_id]}
        final.append(text)

    race_list = final

    if random:
        shuffle(race_list)
    else:
        race_list.sort(key=lambda x: x[category], reverse=True)

    description = ""
    for race in race_list[:10]:
        text_id = race["text_id"]
        description += (
            f"\n\n[#{text_id}]({urls.trdata_text(text_id, universe)}) - "
            f"[{race['wpm']:,.2f} WPM]({urls.replay(username, race['number'])}) - "
            f"**{race['times']:,} time{'s' * (race['times'] != 1)}** - "
            f"[Ghost]({text_list[text_id]['ghost']})\n"
            f'"{strings.truncate_clean(text_list[text_id]["quote"], 60)}"'
        )

    category_title = category
    if category == "wpm":
        category_title = "WPM"

    race_count = len(race_list)
    percent = (race_count / texts_typed) * 100
    description = (
        f"**{race_count:,}** of **{texts_typed:,}** texts are "
        f"{'above' if over else 'below'} {threshold:,} {category_title} "
        f"({percent:,.2f}%){description}"
    )

    if category == "points":
        category_title = f"Point{'s' if threshold != 1 else ''}"
    elif category == "times":
        category_title = f"Time{'s' if threshold != 1 else ''}"

    embed = Embed(
        title=f"Texts {'Over' if over else 'Under'} {threshold:,} "
              f"{category_title}{' (Randomized)' * random}",
        description=description,
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TextsOver(bot))
