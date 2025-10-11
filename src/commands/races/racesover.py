from discord.ext import commands

import database.main.users as users
from database.bot.users import get_user
from database.main import races
from utils import errors, strings
from utils.embeds import Page, Message, is_embed

categories = ["wpm", "points"]
command = {
    "name": "racesover",
    "aliases": ["ro"],
    "description": "Displays the number of races a user has greater than or equal to a category threshold",
    "parameters": "[username] [threshold] <category>",
    "defaults": {
        "category": "wpm",
    },
    "usages": [
        "racesover keegant 300 wpm",
        "racesover joshua728 1000 points",
    ],
}


class RacesOver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def racesover(self, ctx, *args):
        user = get_user(ctx)
        args, user = strings.set_wpm_metric(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, threshold, category = result
        await run(ctx, user, username, threshold, category)


def get_args(user, args, info):
    params = f"username [int] category:{'|'.join(categories)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, threshold, category, over=True):
    if threshold < 0:
        return await ctx.send(embed=errors.greater_than(0))

    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)
    if era_string:
        stats = await users.filter_stats(stats, user)
    text_pool = user["settings"]["text_pool"]
    wpm_metric = user["settings"]["wpm"]

    stats = dict(stats)
    if text_pool == "maintrack":
        race_list = await races.get_races(
            username, columns=["timestamp"], start_date=user["start_date"], end_date=user["end_date"],
            universe=universe, text_pool=text_pool,
        )
        stats["races"] = len(race_list)

    if stats["races"] == 0:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    category_title = {"wpm": "WPM"}.get(category, category.title())
    if category == "wpm":
        category = wpm_metric
    times = users.count_races_over(
        username, threshold, category, over, universe, user["start_date"], user["end_date"],
        text_pool=text_pool,
    )
    description = (
        f"**{times:,}** of **{stats['races']:,}** races are "
        f"{'above' if over else 'below'} {threshold:,} {category_title} "
        f"({times / stats["races"]:.2%})"
    )

    page = Page(
        title=f"Races {'Over' if over else 'Under'} {threshold:,} {category_title}",
        description=description,
    )

    message = Message(
        ctx, user, page,
        profile=stats,
        universe=universe,
        text_pool=text_pool,
        wpm_metric=wpm_metric,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(RacesOver(bot))
