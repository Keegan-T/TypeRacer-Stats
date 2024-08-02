from discord import Embed
from discord.ext import commands

import database.users as users
from database.bot_users import get_user
from utils import errors, embeds, strings

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
        if embeds.is_embed(result):
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

    category_title = "WPM"
    if category != "wpm":
        category_title = category.title()

    times = users.count_races_over(username, category, threshold, over, universe)
    percent = (times / stats["races"]) * 100
    description = (
        f"**{times:,}** of **{stats['races']:,}** races are "
        f"{'above' if over else 'below'} {threshold:,} {category_title} "
        f"({percent:,.2f}%)"
    )

    embed = Embed(
        title=f"Races {'Over' if over else 'Under'} {threshold:,} {category_title}",
        description=description,
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RacesOver(bot))
