from discord.ext import commands

import database.main.users as users
from api.users import get_stats
from commands.account.download import run as download
from database.main import races
from database.bot.users import get_user
from utils import errors, urls, strings, dates
from utils.embeds import Message, get_pages, is_embed

categories = ["recent", "best", "worst"]
command = {
    "name": "textimprovements",
    "aliases": ["ti", "grebs"],
    "description": "Displays a list of a user's most recent text improvements\n"
                   "`sort` can be `best` or `worst`",
    "parameters": "[username] <sort>",
    "defaults": {
        "sort": "recent",
    },
    "usages": [
        "textimprovements keegant",
        "textimprovements charlieog best",
    ],
}


class TextImprovements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textimprovements(self, ctx, *args):
        user = get_user(ctx)
        args, user = dates.set_command_date_range(args, user)
        args, user = strings.set_wpm_metric(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, sort = result
        await run(ctx, user, username, sort)


def get_args(user, args, info):
    params = f"username category:{'|'.join(categories)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, sort):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    api_stats = await get_stats(username, universe=universe)
    await download(racer=api_stats, universe=universe)

    race_list = await races.get_races(
        username, columns=["text_id", "number", "wpm", "timestamp"], universe=universe,
        start_date=user["start_date"], end_date=user["end_date"],
        text_pool=user["settings"]["text_pool"],
    )
    if not race_list:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)
    race_list.sort(key=lambda x: x[3])

    improvements = []
    text_bests = {}
    for race in race_list:
        text_id = race["text_id"]
        if text_id not in text_bests:
            text_bests[text_id] = race
        else:
            best_race = text_bests[text_id]
            difference = race["wpm"] - best_race["wpm"]
            if difference > 0:
                text_bests[text_id] = race
                improvements.append((best_race, race, difference))

    title = "Text Improvements"
    if sort == "recent":
        improvements.reverse()
    elif sort == "best":
        improvements.sort(key=lambda x: x[2], reverse=True)
        title += " (Best)"
    elif sort == "worst":
        improvements.sort(key=lambda x: x[2])
        title += " (Worst)"

    def formatter(data):
        race1, race2, improvement = data
        text_id = race1["text_id"]
        replay1 = urls.replay(username, race1["number"], universe, timestamp=race1['timestamp'])
        replay2 = urls.replay(username, race2["number"], universe, timestamp=race2['timestamp'])
        return (
            f"[{race1['wpm']:,.2f}]({replay1}) ➜ [{race2['wpm']:,.2f}]({replay2}) (+{improvement:,.2f} WPM) - "
            f"[#{text_id}]({urls.trdata_text(text_id, universe)}) - "
            f"{strings.discord_timestamp(race2['timestamp'])}\n"
        )

    pages = get_pages(improvements, formatter, page_count=10, per_page=10)

    message = Message(
        ctx, user, pages,
        title=title,
        profile=stats,
        universe=universe,
        text_pool=user["settings"]["text_pool"],
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(TextImprovements(bot))
