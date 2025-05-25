from discord.ext import commands

from database.main import users, text_results
from database.bot.users import get_user
from utils import errors, strings, urls, dates
from utils.embeds import Message, get_pages, is_embed
from utils.stats import calculate_text_performances

command = {
    "name": "textperformances",
    "aliases": ["tp", "pf", "pw"],
    "description": "Displays your best/worst scores based on a calculated performance metric",
    "parameters": "[username] <sort>",
    "defaults": {
        "sort": "best",
    },
    "usages": ["textperformances keegant"],
}


class TextPerformances(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textperformances(self, ctx, *args):
        user = get_user(ctx)
        args, user = dates.set_command_date_range(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, sort = result
        if ctx.invoked_with == "pw":
            sort = "worst"
        if username == "all":
            await run_all(ctx, user, sort)
        else:
            await run(ctx, user, username, sort)


def get_args(user, args, info):
    params = "username category:best|worst"
    return strings.parse_command(user, params, args, info)


async def run_all(ctx, user, sort):
    text_bests = []
    top_10s = text_results.get_top_10s()
    for text_id, results in top_10s.items():
        text_bests.append(dict(results[0]))

    calculate_text_performances(text_bests)
    text_bests.sort(key=lambda x: x["performance"], reverse=sort == "best")

    def formatter(text):
        text_id = text["text_id"]
        quote = text["quote"]
        username = text["username"]
        quote = strings.truncate_clean(quote, 150)
        return (
            f"{strings.escape_formatting(username)} - [{text['wpm']:,.2f} WPM]"
            f"({urls.replay(username, text['number'])}) - "
            f"{text['performance']:,.0f} Score - "
            f"{strings.discord_timestamp(text["timestamp"])}\n"
            f"[Text #{text_id}]({urls.trdata_text(text_id)}) - "
            f"{text['rating']:,.2f}/10 Difficulty - {len(text['quote'])} characters\n"
            f'"{quote}"\n\n'
        )

    pages = get_pages(text_bests, formatter, page_count=20, per_page=5)

    message = Message(
        ctx=ctx,
        user=user,
        pages=pages,
        title=f"{sort.title()} Text Performances (All Users)",
    )

    await message.send()


async def run(ctx, user, username, sort):
    universe = user["universe"]
    era_string = strings.get_era_string(user)

    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    if era_string:
        text_bests = await users.get_text_bests_time_travel(username, universe, user, race_stats=True)
    else:
        text_bests = users.get_text_bests(username, universe=universe, race_stats=True)

    if not text_bests:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    calculate_text_performances(text_bests, universe)
    text_bests.sort(key=lambda x: x["performance"], reverse=sort == "best")

    def formatter(text):
        text_id = text["text_id"]
        quote = text["quote"]
        quote = strings.truncate_clean(quote, 120)
        return (
            f"[{text['wpm']:,.2f} WPM]({urls.replay(username, text['number'], universe)}) - "
            f"{text['performance']:,.0f} Score - "
            f"{strings.discord_timestamp(text["timestamp"])}\n"
            f"[Text #{text_id}]({urls.trdata_text(text_id, universe)}) - "
            f"{text['rating']:,.2f}/10 Difficulty - {len(text['quote'])} characters\n"
            f'"{quote}"\n\n'
        )

    texts_typed = len(text_bests)
    total = sum([text["performance"] for text in text_bests])
    average = total / texts_typed

    header = (
        f"**Text Performance Average:** {average:,.0f} Score\n"
        f"**Texts Typed:** {texts_typed:,}\n"
        f"**Text Performance Total:** {total:,.0f} Score\n\n"
    )

    pages = get_pages(text_bests, formatter, page_count=20, per_page=5)

    message = Message(
        ctx=ctx,
        user=user,
        pages=pages,
        title=f"{sort.title()} Text Performances",
        header=header,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(TextPerformances(bot))
