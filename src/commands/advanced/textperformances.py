from discord.ext import commands

from database import users, texts, text_results
from database.bot_users import get_user
from database.texts import update_text_difficulties
from utils import errors, strings, urls, dates
from utils.embeds import Message, get_pages, is_embed

command = {
    "name": "textperformances",
    "aliases": ["tp", "pf"],
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
        if username == "all":
            await run_all(ctx, user, sort)
        else:
            await run(ctx, user, username, sort)


def get_args(user, args, info):
    params = "username category:best|worst"
    return strings.parse_command(user, params, args, info)


def get_performance_list(text_bests, universe):
    performance_list = []
    text_dict = texts.get_texts(as_dictionary=True, include_disabled=False, universe=universe)
    if next(iter(text_dict.items()))[1]["difficulty"] is None:
        update_text_difficulties(universe)
        text_dict = texts.get_texts(as_dictionary=True, include_disabled=False, universe=universe)
    text_list = [{"text_id": k, "difficulty": v["difficulty"]} for k, v in text_dict.items()]
    difficulties = {text["text_id"]: text["difficulty"] for text in text_list}
    min_difficulty = min(text["difficulty"] for text in text_list)
    max_difficulty = max(text["difficulty"] for text in text_list)

    for text in text_bests:
        race = dict(text)
        text_id = text["text_id"]
        wpm = text["wpm"]
        quote = text_dict[text_id]["quote"]
        difficulty = difficulties[text_id]
        performance = wpm ** 1.5 * difficulty ** 1.2
        rating = ((difficulty - min_difficulty) / (max_difficulty - min_difficulty)) * 10
        race.update({
            "quote": quote,
            "difficulty": difficulty,
            "performance": performance,
            "rating": rating
        })
        performance_list.append(race)

    return performance_list


async def run_all(ctx, user, sort):
    text_bests = []
    top_10s = text_results.get_top_10s()
    for text_id, results in top_10s.items():
        text_bests.append(dict(results[0]))

    performance_list = get_performance_list(text_bests, "play")
    performance_list.sort(key=lambda x: x["performance"], reverse=sort == "best")

    def formatter(text):
        text_id = text["text_id"]
        quote = text["quote"]
        username = text["username"]
        quote = strings.truncate_clean(quote, 150)
        return (
            f"{strings.escape_discord_format(username)} - [{text['wpm']:,.2f} WPM]"
            f"({urls.replay(username, text['number'])}) - "
            f"{text['performance']:,.0f} Score - "
            f"{strings.discord_timestamp(text["timestamp"])}\n"
            f"[Text #{text_id}]({urls.trdata_text(text_id)}) - "
            f"{text['rating']:,.2f}/10 Difficulty - {len(text['quote'])} characters\n"
            f'"{quote}"\n\n'
        )

    pages = get_pages(performance_list, formatter, page_count=20, per_page=5)

    message = Message(
        ctx=ctx,
        user=user,
        pages=pages,
        title=f"{sort.title()} Text Performances (All Users)",
    )

    await message.send()


async def run(ctx, user, username, sort):
    universe = user["universe"]

    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    if not user["start_date"] and not user["end_date"]:
        text_bests = users.get_text_bests(username, universe=universe, race_stats=True)
    else:
        text_bests = await users.get_text_bests_time_travel(username, universe, user, race_stats=True)

    performance_list = get_performance_list(text_bests, universe)
    performance_list.sort(key=lambda x: x["performance"], reverse=sort == "best")

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

    texts_typed = len(performance_list)
    total = sum([text["performance"] for text in performance_list])
    average = total / texts_typed

    header = (
        f"**Text Performance Average:** {average:,.0f} Score\n"
        f"**Texts Typed:** {texts_typed:,}\n"
        f"**Text Performance Total:** {total:,.0f} Score\n\n"
    )

    pages = get_pages(performance_list, formatter, page_count=20, per_page=5)

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
