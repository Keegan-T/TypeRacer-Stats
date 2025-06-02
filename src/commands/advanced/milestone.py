from discord import Embed
from discord.ext import commands

import commands.recent as recent
import database.main.races as races
import database.main.texts as texts
import database.main.users as users
from api.races import get_race
from commands.basic.race import add_stats
from database.bot.users import get_user
from utils import errors, urls, embeds, strings, dates

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
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, milestone, category = result

        await run(ctx, user, username, milestone, category)


def get_args(user, args, info):
    params = f"username [int] category:{'|'.join(categories)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, milestone, category):
    if milestone <= 0:
        return await ctx.send(embed=errors.greater_than(0))

    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    category_title = "WPM"
    if category != "wpm":
        category_title = category.title()

    embed = Embed(title=f"Milestone - {milestone:,} {category_title}", color=user["colors"]["embed"])
    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    milestone_number = users.get_milestone_number(
        username, milestone, category, universe, user["start_date"], user["end_date"]
    )
    if not milestone_number:
        embed.description = "User has not achieved this milestone"
        return await ctx.send(embed=embed, content=era_string)

    embed.title += f" - Race #{milestone_number:,}"
    embed.url = urls.replay(username, milestone_number, universe)

    race_info = await get_race(username, milestone_number, universe=universe)
    if not race_info:
        text_list = texts.get_texts(as_dictionary=True, universe=universe)
        race_info = dict(races.get_race(username, milestone_number, universe))
        text = text_list[race_info["text_id"]]
        race_info["quote"] = text["quote"]

    add_stats(embed, race_info, universe)
    time_taken = strings.format_duration_short(race_info["timestamp"] - stats["joined"])
    fields = list(embed.fields)
    field = {
        "name": fields[0].name,
        "value": fields[0].value + "\nTook " + time_taken,
    }
    embed.clear_fields()
    embed.add_field(**field)

    await ctx.send(embed=embed, content=era_string)

    recent.text_id = race_info["text_id"]


async def setup(bot):
    await bot.add_cog(Milestone(bot))
