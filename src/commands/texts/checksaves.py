from datetime import datetime

from discord.ext import commands

import database.main.races as races
import database.bot.recent_text_ids as recent
import database.main.texts as texts
import database.main.users as users
from api.users import get_stats
from commands.account.download import run as download
from database.bot.users import get_user
from utils import errors, urls, strings
from utils.embeds import Page, Message, is_embed

command = {
    "name": "checksaves",
    "aliases": ["charlieog", "cs", "cog"],
    "description": "Displays the number of times you've raced a quote within the last 24 hours",
    "parameters": "[username] <text_id>",
    "defaults": {
        "text_id": 3621293,
    },
    "usages": ["checksaves keegant 3810446"],
    "temporal": False,
}


class CheckSaves(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def checksaves(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command, ctx.channel.id)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, text_id = result
        await run(ctx, user, username, text_id)


def get_args(user, args, info, channel_id):
    params = "username"
    username = strings.parse_command(user, params, args, info)[0]
    text_id = None
    if len(args) > 1:
        if args[1] == "^":
            text_id = recent.get_recent(channel_id)
        else:
            text_id = args[1]

    return username, text_id


async def run(ctx, user, username, text_id):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    api_stats = await get_stats(username, universe=universe)
    await download(racer=api_stats, universe=universe)

    if text_id is None:
        if ctx.author.id == 108328502591250432:
            text_id = 3621293
        else:
            race_number = api_stats["races"]
            race = await races.get_race(username, race_number, universe)
            text_id = race["text_id"] if race else 3621293

    text = texts.get_text(text_id, universe)
    if text is None:
        return await ctx.send(embed=errors.unknown_text(universe))

    max_saves = 10
    description = (
        f'**Text** [#{text_id}]({urls.trdata_text(text_id, universe)}) - [Ghost]({text["ghost"]})\n'
        f'"{strings.truncate_clean(text["quote"], 1000)}"'
    )

    race_list = races.get_text_races(username, text_id, universe)
    recent_scores = []
    now = datetime.now().timestamp()

    for i, race in enumerate(race_list[::-1]):
        if race["timestamp"] < now - 86400:
            break
        recent_scores.append(race)

    recent_saves = len(recent_scores)
    available_saves = max(max_saves - recent_saves, 0)

    if available_saves == 0:
        description += f"\n\nNext save available {strings.discord_timestamp(recent_scores[-1]['timestamp'] + 86400)}\n"
    else:
        description += f"\n\n{available_saves:,} save{'s' * (available_saves != 1)} available now\n"

    if recent_saves > 0:
        description += "\n**Recent Saves**\n"
        if len(recent_scores) > 20:
            description += f"[Truncated {len(recent_scores) - 20} Scores]\n"
        for score in recent_scores[:20][::-1]:
            description += (
                f"{strings.format_duration(now - score['timestamp'])} ago - "
                f"[{score['wpm']:,.2f} WPM]({urls.replay(username, score['number'], universe)})\n"
            )

    message = Message(
        ctx, user, Page(
            title=f"Available Saves",
            description=description,
        ),
        universe=universe,
        time_travel=False,
    )

    await message.send()

    recent.update_recent(ctx.channel.id, text_id)


async def setup(bot):
    await bot.add_cog(CheckSaves(bot))
