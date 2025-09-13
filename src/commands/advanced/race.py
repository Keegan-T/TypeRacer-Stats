from discord.ext import commands

import database.bot.recent_text_ids as recent
import database.main.races as races
import database.main.texts as texts
from api.users import get_stats
from commands.account.download import run as download
from commands.basic.realspeed import get_args
from config import prefix
from database.bot.users import get_user
from database.main import users
from utils import errors, urls, strings
from utils.embeds import Page, Field, Message, is_embed

command = {
    "name": "race",
    "aliases": ["r"],
    "description": "Displays information about a user's race\n"
                   f"`{prefix}race [username] <-n>` will return real speeds for n races ago",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number"
    },
    "usages": [
        "race keegant 100000",
        "race keegant -1",
    ],
}


class Race(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def race(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command, ctx.channel.id)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, universe)


async def run(ctx, user, username, race_number, universe):
    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    stats = get_stats(username, universe=universe)
    await download(racer=stats, universe=universe)

    if race_number < 1:
        race_number = stats["races"] + race_number

    race_info = races.get_race(username, race_number, universe)
    if not race_info:
        return await ctx.send(embed=errors.race_not_found(username, race_number, universe))
    race_info = dict(race_info)
    quote = texts.get_text(race_info["text_id"])["quote"]
    race_info["quote"] = quote
    race_info["lagged"] = race_info["wpm"]

    description, field = get_stat_fields(race_info, universe)
    page = Page(
        title=f"Race #{race_number:,}",
        description=description,
        fields=field
    )

    message = Message(
        ctx, user, page,
        url=urls.replay(username, race_number, universe),
        profile=stats,
        universe=universe,
    )

    await message.send()

    recent.update_recent(ctx.channel.id, race_info["text_id"])


def get_stat_fields(race_info, universe):
    description = strings.text_description(race_info, universe)
    rank = race_info["rank"]
    racers = race_info["racers"]
    outcome = "Loss"
    if rank == 1:
        outcome = "Practice" if racers == 1 else "Win"

    wpm = race_info.get("wpm_adjusted", race_info["wpm"])
    if "total_time" in race_info:
        seconds = race_info["total_time"] / 1000
    else:
        seconds = len(race_info["quote"]) * 12 / wpm
    accuracy_string = ""
    if race_info["accuracy"] != 0:
        accuracy_string = f" ({race_info['accuracy']:,.2%} Accuracy)"
    stats_string = (
        f"**Speed:** {wpm:,.2f} WPM{accuracy_string}\n"
        f"**Points:** {race_info['points']:,.2f}\n"
        f"**Race Time:** {strings.format_duration(seconds, False)}\n"
        f"**Outcome:** {outcome} ({rank}/{racers})\n\n"
        f"Completed {strings.discord_timestamp(race_info['timestamp'])}"
    )

    field = Field(
        name="Stats",
        value=stats_string,
        inline=False,
    )

    return description, field


async def setup(bot):
    await bot.add_cog(Race(bot))
