import math

from discord import Embed
from discord.ext import commands

import database.texts as texts
import database.users as users
from config import prefix
from database.bot_users import get_user
from utils import errors, urls, strings, embeds

categories = ["best", "worst", "old", "new", "accuracy"]
command = {
    "name": "textbests",
    "aliases": ["tb"],
    "description": "Displays a user's text best average and their best texts\n"
                   "Providing `n` will display the average of the user's top n texts\n"
                   f"`{prefix}textbests [username] worst` will show the user's worst quotes",
    "parameters": "[username] <n/category>",
    "usages": [
        "textbests keegant",
        "textbests keegant worst",
        "textbests keegant old",
        "textbests keegant new",
        "textbests keegant accuracy",
        "textbests charlieog 100",
    ],
}


class TextBests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textbests(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, sort, n = result
        await run(ctx, user, username, sort, n)


def get_args(user, args, info):
    n = 99999
    sort = "best"

    params = f"username choice:{'|'.join(categories)}"
    result = strings.parse_command(user, params, args, info)
    if embeds.is_embed(result):
        if len(args) > 1:
            try:
                username = args[0]
                if user["username"] and username == "me":
                    username = user["username"]
                n = strings.parse_value_string(args[1])
                return username, sort, n
            except ValueError:
                pass

        return errors.invalid_choice("sort", categories)
    else:
        username, sort = result

    return username, sort, n


async def run(ctx, user, username, sort, n):
    if n < 1:
        return await ctx.send(embed=errors.greater_than(0))

    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)
    if era_string:
        stats = await users.time_travel_stats(stats, user)

    text_list = texts.get_texts(as_dictionary=True, universe=universe)
    if era_string:
        text_bests = await users.get_text_bests_time_travel(username, universe, user, race_stats=True)
    else:
        text_bests = users.get_text_bests(username, universe=universe, race_stats=True)

    if len(text_bests) == 0:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    if sort in ["new", "old"]:
        text_bests.sort(key=lambda x: x["timestamp"])
    elif sort == "accuracy":
        text_bests.sort(key=lambda x: x["accuracy"])
    if sort in ["worst", "new"]:
        text_bests.reverse()
    text_bests = text_bests[:n]
    texts_typed = len(text_bests)
    total_text_wpm = sum(text["wpm"] for text in text_bests)
    average = total_text_wpm / texts_typed
    next_milestone = 5 * math.ceil(average / 5)
    required_wpm_gain = texts_typed * next_milestone - total_text_wpm

    description = (
        f"**Text Best Average:** {average:,.2f} WPM\n"
        f"**Texts Typed:** {texts_typed:,}\n"
        f"**Text WPM Total:** {total_text_wpm:,.0f} WPM\n"
        f"**Gain Until {next_milestone} Average:** {required_wpm_gain:,.0f} WPM\n"
    )

    limit = 10
    scores = ""

    for text in text_bests[:limit]:
        text_id = text["text_id"]
        quote = strings.truncate_clean(text_list[text_id]["quote"], 60)
        race_stat = f"{text['accuracy'] * 100}% Accuracy - " if sort == "accuracy" else f"Race #{text['number']:,} - "
        scores += (
            f"[{text['wpm']:,.2f} WPM]({urls.replay(username, text['number'], universe)}) - "
            f"{race_stat}"
            f"[Text #{text_id}]({urls.trdata_text(text_id, universe)}) - "
            f'{strings.discord_timestamp(text["timestamp"])}\n"{quote}"\n\n'
        )

    title = f"Text Bests"
    if n < stats["texts_typed"]:
        title += f" (Top {n:,} Texts)"
    elif sort == "worst":
        title += " (Worst Texts)"
    elif sort == "new":
        title += " (Newest)"
    elif sort == "old":
        title += " (Oldest)"
    elif sort == "accuracy":
        title += " (Worst Accuracy)"

    embed = Embed(
        title=title,
        description=f"{description}\n{scores}",
        color=user["colors"]["embed"],
        url=urls.trdata_text_analysis(username, universe),
    )

    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)


async def setup(bot):
    await bot.add_cog(TextBests(bot))
