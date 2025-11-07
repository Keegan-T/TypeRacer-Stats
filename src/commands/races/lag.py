from discord.ext import commands

import database.bot.recent_text_ids as recent
import database.main.races as races
import database.main.texts as texts
from api.races import get_universe_multiplier
from api.users import get_stats
from commands.account.download import run as download
from commands.races.realspeed import get_args
from config import prefix
from database.bot.users import get_user
from database.main import users
from utils import errors, urls, strings
from utils.embeds import Page, Field, Message, is_embed

command = {
    "name": "lag",
    "aliases": [],
    "description": "Displays lag information about a user's race\n"
                   f"`{prefix}race [username] <-n>` will return from n races ago",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number"
    },
    "usages": [
        "lag keegant 100000",
        "lag keegant -1",
    ],
}


class Lag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def lag(self, ctx, *args):
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

    stats = await get_stats(username, universe=universe)
    await download(racer=stats, universe=universe)

    if race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await races.get_race(username, race_number, universe)
    if not race_info:
        return await ctx.send(embed=errors.race_not_found(username, race_number, universe))
    race_info = dict(race_info)
    quote = texts.get_text(race_info["text_id"], universe)["quote"]
    race_info["quote"] = quote
    race_info["lagged"] = race_info["wpm"]

    description, field = get_stat_fields(race_info, universe)
    page = Page(
        title=f"Lag Values for Race #{race_number:,}",
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
    description = (
        f"Completed {strings.discord_timestamp(race_info['timestamp'])}\n\n" +
        strings.text_description(race_info, universe)
    )

    lagged = race_info.get("wpm")
    unlagged = race_info.get("wpm_unlagged")
    adjusted = race_info.get("wpm_adjusted", race_info["wpm"])
    start_time = race_info.get("start_time") or 0
    duration = race_info.get("total_time")
    lagged_ms = get_universe_multiplier(universe) * len(race_info["quote"]) / lagged if lagged > 0 else 0
    ping = round(lagged_ms) - duration
    lag = unlagged - lagged
    stats_string = (
        f"**Lagged:** {lagged:,.2f} WPM ({lag:,.2f} WPM lag)\n"
        f"**Unlagged:** {unlagged:,.2f} WPM ({ping:,.0f}ms ping)\n"
        f"**Adjusted:** {adjusted:,.2f} WPM ({start_time:,.0f}ms start)"
    )

    field = Field(
        name="Stats",
        value=stats_string,
        inline=False,
    )

    return description, field


async def setup(bot):
    await bot.add_cog(Lag(bot))
