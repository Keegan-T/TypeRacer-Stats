from discord import Embed
from discord.ext import commands
import utils
import errors
import urls
from database.bot_users import get_user
from api.races import get_race_info
from commands.basic.race import add_stats
import commands.recent as recents
import database.users as users
import database.races as races
import database.texts as texts

categories = ["races", "points", "wpm", "texts"]
info = {
    "name": "milestone",
    "aliases": ["ms"],
    "description": "Displays the race upon which a user achieved a milestone",
    "parameters": "[username] [milestone] [category]",
    "usages": [
        "milestone keegant 500000 races",
        "milestone wordracer888 10m points",
        "milestone deroche1 300 wpm",
        "milestone rektless 10k texts",
    ],
    "import": True,
}


class Milestone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def milestone(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, milestone, category = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, milestone, category)


async def get_params(ctx, user, params):
    if len(params) < 3:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    username = user["username"]

    if params[0].lower() != "me":
        username = params[0]

    milestone = params[1]
    try:
        milestone = utils.parse_value_string(milestone)
    except ValueError:
        await ctx.send(embed=errors.invalid_number_format())
        raise

    if milestone <= 0:
        await ctx.send(embed=errors.greater_than(0))
        raise ValueError

    category = utils.get_category(categories, params[2])
    if not category:
        await ctx.send(embed=errors.invalid_option("category", categories))
        raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), milestone, category


async def run(ctx, user, username, milestone, category):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    category_title = "WPM"
    if category != "wpm":
        category_title = category.title()

    embed = Embed(title=f"Milestone - {milestone:,} {category_title}", color=user["colors"]["embed"])
    utils.add_profile(embed, stats)

    milestone_number = users.get_milestone_number(username, milestone, category)
    if not milestone_number:
        embed.description = "User has not achieved this milestone"
        return await ctx.send(embed=embed)

    embed.title += f" - Race #{milestone_number:,}"
    embed.url = urls.replay(username, milestone_number)

    race_info = await get_race_info(username, milestone_number, get_lagged=True)
    if not race_info:
        text_list = texts.get_texts(as_dictionary=True)
        race_info = dict(races.get_race(username, milestone_number))
        text = text_list[race_info["text_id"]]
        race_info["quote"] = text["quote"]

    add_stats(embed, race_info)

    await ctx.send(embed=embed)

    recents.text_id = race_info["text_id"]


async def setup(bot):
    await bot.add_cog(Milestone(bot))
