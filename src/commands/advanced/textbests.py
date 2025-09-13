import math

from discord.ext import commands

import database.main.texts as texts
import database.main.users as users
from config import prefix
from database.bot.users import get_user
from utils import errors, urls, strings
from utils.embeds import get_pages, Message, is_embed

categories = ["best", "worst", "old", "new", "accuracy"]
command = {
    "name": "textbests",
    "aliases": ["tb"],
    "description": "Displays a user's text best average and their best texts\n"
                   "Providing `n` will display the average of the user's top n texts\n"
                   f"`{prefix}textbests [username] worst` will show the user's worst quotes\n",
    "parameters": "[username] <n/category>",
    "usages": [
        "textbests keegant",
        "textbests keegant worst",
        "textbests keegant old",
        "textbests keegant new",
        "textbests keegant accuracy",
        "textbests charlieog 100",
        "textbests keegant raw",
    ],
}


class TextBests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textbests(self, ctx, *args):
        user = get_user(ctx)

        raw = False
        if args and args[-1] == "raw":
            raw = True
            args = args[:-1]

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, sort, n = result
        await run(ctx, user, username, sort, n, raw)


def get_args(user, args, info):
    n = 99999
    sort = "best"

    params = f"username choice:{'|'.join(categories)}"
    result = strings.parse_command(user, params, args, info)
    if is_embed(result):
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


async def run(ctx, user, username, sort, n, raw):
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
        text_bests = await users.get_text_bests_time_travel(username, universe, user, race_stats=True, raw=raw)
    else:
        text_bests = users.get_text_bests(username, universe=universe, race_stats=True, raw=raw)

    if len(text_bests) == 0:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    if sort in ["new", "old"]:
        text_bests.sort(key=lambda x: x["timestamp"], reverse=sort == "new")
    elif sort == "accuracy":
        text_bests.sort(key=lambda x: x["accuracy"])
    elif sort == "worst":
        text_bests.reverse()
    text_bests = text_bests[:n]
    texts_typed = len(text_bests)
    total_text_wpm = sum(text["wpm"] for text in text_bests)
    average = total_text_wpm / texts_typed
    next_milestone = 5 * math.ceil(average / 5)
    required_wpm_gain = texts_typed * next_milestone - total_text_wpm

    header = (
        f"**Text Best Average:** {average:,.2f} WPM\n"
        f"**Texts Typed:** {texts_typed:,}\n"
        f"**Text WPM Total:** {total_text_wpm:,.0f} WPM\n"
        f"**Gain Until {next_milestone} Average:** {required_wpm_gain:,.0f} WPM\n\n"
    )

    def formatter(text):
        text_id = text["text_id"]
        quote = strings.truncate_clean(text_list[text_id]["quote"], 60)
        return (
            f"[{text['wpm']:,.2f} WPM]({urls.replay(username, text['number'], universe)})"
            f" ({text['accuracy']:.2%}) - "
            f"[Text #{text_id}]({urls.trdata_text(text_id, universe)}) - "
            f'{strings.discord_timestamp(text["timestamp"])}\n"{quote}"\n\n'
        )

    title = f"Text Bests{' (Raw Speed)' * raw}"
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

    pages = get_pages(text_bests, formatter, page_count=10, per_page=10)

    message = Message(
        ctx, user, pages,
        title=title,
        header=header,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(TextBests(bot))
