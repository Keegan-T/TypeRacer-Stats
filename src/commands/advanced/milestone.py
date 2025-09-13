from discord.ext import commands

import database.main.races as races
import database.bot.recent_text_ids as recent
import database.main.texts as texts
import database.main.users as users
from commands.advanced.race import get_stat_fields
from database.bot.users import get_user
from utils import errors, urls, strings
from utils.embeds import Page, Message, is_embed

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

        result = get_args(user, args, command, ctx.channel.id)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, milestone, category = result

        await run(ctx, user, username, milestone, category)


def get_args(user, args, info, channel_id):
    params = f"username [int] category:{'|'.join(categories)}"

    return strings.parse_command(user, params, args, info, channel_id)


async def run(ctx, user, username, milestone, category):
    if milestone <= 0:
        return await ctx.send(embed=errors.greater_than(0))

    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    category_title = {"wpm": "WPM"}.get(category, category.title())
    page = Page(title=f"Milestone - {milestone:,} {category_title}")

    milestone_number = users.get_milestone_number(
        username, milestone, category, universe, user["start_date"], user["end_date"]
    )
    if not milestone_number:
        page.description = "User has not achieved this milestone"
        message = Message(ctx, user, page, profile=stats, universe=universe)
        return await message.send()

    page.title += f" - Race #{milestone_number:,}"
    url = urls.replay(username, milestone_number, universe)

    race_info = races.get_race(username, milestone_number, universe, get_log=True)
    if not race_info:
        text_list = texts.get_texts(as_dictionary=True, universe=universe)
        race_info = dict(races.get_race(username, milestone_number, universe))
        text = text_list[race_info["text_id"]]
        race_info["quote"] = text["quote"]

    description, field = get_stat_fields(race_info, universe)
    time_taken = strings.format_duration(race_info["timestamp"] - stats["joined"])
    field.value += "\nTook " + time_taken
    page.description = description
    page.fields = [field]

    message = Message(
        ctx, user, page,
        url=url,
        profile=stats,
        universe=universe,
    )

    await message.send()

    recent.update_recent(ctx.channel.id, race_info["text_id"])


async def setup(bot):
    await bot.add_cog(Milestone(bot))
