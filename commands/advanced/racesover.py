from discord import Embed
from discord.ext import commands
import utils
import errors
from database.bot_users import get_user
import database.users as users

categories = ["wpm", "points"]
info = {
    "name": "racesover",
    "aliases": ["ro"],
    "description": "Displays the number of races a user has greater than or equal to a category threshold",
    "parameters": "[username] [threshold] [category]",
    "usages": [
        "racesover keegant 300 wpm",
        "racesover joshua728 1000 points",
    ],
    "import": True,
}


class RacesOver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def racesover(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, threshold, category = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, threshold, category)


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

    if threshold < 0:
        await ctx.send(embed=errors.greater_than(0))
        raise ValueError

    category = utils.get_category(categories, params[2])
    if not category:
        await ctx.send(embed=errors.invalid_option("category", categories))
        raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), threshold, category


async def run(ctx, user, username, threshold, category, over=True):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    category_title = "WPM"
    if category != "wpm":
        category_title = category.title()

    times = users.count_races_over(username, category, threshold, over)
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
    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RacesOver(bot))
