from discord import Embed
from discord.ext import commands
import utils
import errors
import urls
import database.users as users
import database.races as races
import database.texts as texts
import commands.recent as recent
from database.bot_users import get_user
from api.users import get_stats
from datetime import datetime
from commands.basic.download import run as download

command = {
    "name": "checksaves",
    "aliases": ["charlieog", "cs", "cog"],
    "description": "Displays the number of times you've raced a quote within the last 24 hours",
    "parameters": "[username] <text_id>",
    "defaults": {
        "text_id": 3621293,
    },
    "usages": ["checksaves keegant 3810446"],
}


class CheckSaves(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def checksaves(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, text_id = result
        await run(ctx, user, username, text_id)


def get_args(user, args, info):
    params = "username text_id:3621293"

    return utils.parse_command(user, params, args, info)


async def run(ctx, user, username, text_id):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    api_stats = get_stats(username)
    await download(stats=api_stats)

    text = texts.get_text(text_id)
    if text is None:
        return await ctx.send(embed=errors.unknown_text())

    max_saves = 10
    description = (
        f'**Text** [#{text_id}]({urls.trdata_text(text_id)}) - [Ghost]({text["ghost"]})\n'
        f'"{utils.truncate_clean(text["quote"], 1000)}"'
    )

    race_list = races.get_text_races(username, text_id)
    recent_scores = []
    now = datetime.now().timestamp()

    for i, race in enumerate(race_list[::-1]):
        if race["timestamp"] < now - 86400:
            break
        recent_scores.append(race)

    recent_saves = len(recent_scores)
    available_saves = max(max_saves - recent_saves, 0)

    if available_saves == 0:
        description += f"\n\nNext save available <t:{int(recent_scores[-1]['timestamp'] + 86400)}:R>\n"
    else:
        description += f"\n\n{available_saves:,} save{'s' * (available_saves != 1)} available now\n"

    if recent_saves > 0:
        description += "\n**Recent Saves**\n"
        for score in recent_scores[::-1]:
            description += (
                f"{utils.format_duration_short(now - score['timestamp'])} ago - "
                f"[{score['wpm']:,} WPM]({urls.replay(username, score['number'])})\n"
            )

    embed = Embed(
        title=f"Available Saves",
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, api_stats)

    await ctx.send(embed=embed)
    recent.text_id = text_id


async def setup(bot):
    await bot.add_cog(CheckSaves(bot))
