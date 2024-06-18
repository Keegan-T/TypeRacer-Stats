from discord import Embed
from discord.ext import commands
import utils
import errors
import urls
from database.bot_users import get_user
from api.races import get_race
from commands.basic.race import add_stats
import commands.recent as recent
import database.users as users
import database.races as races
import database.texts as texts

categories = ["races", "points", "wpm", "texts"]
command = {
    "name": "milestone",
    "aliases": ["ms"],
    "description": "Displays the race upon which a user achieved a milestone",
    "parameters": "[username] [milestone] <category>",
    "defualts": {
        "category": "races",
    },
    "usages": [
        "milestone keegant 500000 races",
        "milestone wordracer888 10m points",
        "milestone deroche1 300 wpm",
        "milestone rektless 10k texts",
    ],
}


class Milestone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def milestone(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, milestone, category = result

        await run(ctx, user, username, milestone, category)


def get_args(user, args, info):
    params = f"username [int] category:{'|'.join(categories)}"

    return utils.parse_command(user, params, args, info)


async def run(ctx, user, username, milestone, category):
    if milestone <= 0:
        return await ctx.send(embed=errors.greater_than(0))

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

    race_info = await get_race(username, milestone_number)
    if not race_info:
        text_list = texts.get_texts(as_dictionary=True)
        race_info = dict(races.get_race(username, milestone_number))
        text = text_list[race_info["text_id"]]
        race_info["quote"] = text["quote"]

    add_stats(embed, race_info)

    await ctx.send(embed=embed)

    recent.text_id = race_info["text_id"]


async def setup(bot):
    await bot.add_cog(Milestone(bot))
