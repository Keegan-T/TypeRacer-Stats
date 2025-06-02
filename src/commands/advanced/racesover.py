from discord.ext import commands

import database.main.users as users
from database.bot.users import get_user
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
        stats = await users.time_travel_stats(stats, user)

    if stats["races"] == 0:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    category_title = {"wpm": "WPM"}.get(category, category.title())
    times = users.count_races_over(
        username, threshold, category, over, universe, user["start_date"], user["end_date"]
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
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(RacesOver(bot))
