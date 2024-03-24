from discord import Embed
from discord.ext import commands
from src import urls, errors, utils
from random import shuffle
from database.bot_users import get_user
import database.users as users
import database.texts as texts

categories = ["wpm", "points", "times"]
info = {
    "name": "textsover",
    "aliases": ["to"],
    "description": "Displays the number of texts a user has greater than or equal to a category threshold\n"
                   "Add `random` as a parameter to randomize the order in which texts are displayed",
    "parameters": "[username] [threshold] [category]",
    "usages": [
        "textsover joshua728 1000 points",
        "textsover charlieog 5000 times",
        "textsover keegant 200 wpm random",
    ],
    "import": True,
}


class TextsOver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def textsover(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, threshold, category, random = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, threshold, category, random=random)


async def get_params(ctx, user, params, command=info):
    if len(params) < 3:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    username = user["username"]

    if params[0].lower() != "me":
        username = params[0]

    threshold = params[1]
    try:
        threshold = utils.parse_value_string(threshold)
    except ValueError:
        await ctx.send(embed=errors.invalid_number_format())
        raise

    if threshold <= 0:
        await ctx.send(embed=errors.greater_than(0))
        raise ValueError

    category = utils.get_category(categories, params[2])
    if not category:
        await ctx.send(embed=errors.invalid_option("category", categories))
        raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    random = False
    if len(params) > 3:
        if params[3] in ["random", "rand", "r"]:
            random = True

    return username.lower(), threshold, category, random


async def run(ctx, user, username, threshold, category, over=True, random=False):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    texts_typed = stats["texts_typed"]
    description = ""
    text_list = texts.get_texts(as_dictionary=True)

    if over:
        race_list = users.get_texts_over(username, threshold, category)

    else:
        race_list = users.get_texts_under(username, threshold, category)

    if random:
        shuffle(race_list)

    for race in race_list[:10]:
        text_id = race["text_id"]
        description += (
            f"\n\n[#{text_id}]({urls.trdata_text(text_id)}) - **{race['times']:,} time"
            f"{'s' * (race['times'] != 1)}** - [Ghost]({text_list[text_id]['ghost']})\n"
            f'"{utils.truncate_clean(text_list[text_id]["quote"], 60)}"'
        )

    category_title = category
    if category == "wpm":
        category_title = "WPM"

    race_count = len(race_list)
    percent = (race_count / texts_typed) * 100
    description = (
            f"**{race_count:,}** of **{texts_typed:,}** texts are " +
            f"{'above' if over else 'below'} {threshold:,} {category_title} "
            f"({percent:,.2f}%)" + description
    )

    if category == "points":
        category_title = f"Point{'s' if threshold != 1 else ''}"
    elif category == "times":
        category_title = f"Time{'s' if threshold != 1 else ''}"

    embed = Embed(
        title=f"Texts {'Over' if over else 'Under'} {threshold:,} {category_title}",
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TextsOver(bot))
