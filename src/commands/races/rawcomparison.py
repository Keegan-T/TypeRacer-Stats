from discord.ext import commands

import database.bot.recent_text_ids as recent
from api.users import get_stats
from commands.account.download import run as download
from commands.races.realspeed import get_args
from config import prefix
from database.bot.users import get_user
from database.main import users, races
from graphs import match_graph
from utils import errors, urls, strings
from utils.embeds import Page, Message, is_embed
from utils.strings import real_speed_fields

command = {
    "name": "rawcomparison",
    "aliases": ["rc", "poem", "pauseless", "p"],
    "description": "Displays an overlay of adjusted and raw adjusted speed of a race\n"
                   f"`{prefix}rawcomparison [username] <-n>` will display the comparison for n races ago\n"
                   f"`{prefix}pauseless` to view pauseless stats",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number"
    },
    "usages": [
        "rawcomparison poem 222222",
        "rawcomparison storm -1",
    ],
}


class RawComparison(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def rawcomparison(self, ctx, *args):
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

    race = races.get_race(username, race_number, universe, get_log=True, get_keystrokes=True, get_typos=True)
    if not race or not race.get("keystroke_wpm_adjusted", None):
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))

    description = "Completed " + strings.discord_timestamp(race["timestamp"]) + "\n\n" + strings.text_description(race, universe)
    graph_title = f"Race Graph - {username} - Race #{race_number:,}"
    y_label = "Adjusted vs. Raw WPM"
    adjusted_ranking = {
        "username": "Adjusted",
        "keystroke_wpm": race["keystroke_wpm_adjusted"],
    }

    def render_raw():
        rankings = [
            {
                "username": "Raw Adjusted",
                "keystroke_wpm": race["keystroke_wpm_raw_adjusted"],
            },
            adjusted_ranking
        ]

        return match_graph.render(
            user, rankings, graph_title, y_label, universe,
            markers=[race["typos"], []]
        )

    def render_pauseless():
        rankings = [
            {
                "username": "Pauseless",
                "keystroke_wpm": race["keystroke_wpm_pauseless_adjusted"],
            },
            adjusted_ranking,
        ]

        return match_graph.render(
            user, rankings, graph_title, y_label, universe,
            markers=[race["typos"], race["pauses"]]
        )

    pages = [
        Page(
            title=f"Real vs. Raw Speed - Race #{race_number:,}",
            description = description,
            fields=real_speed_fields(race),
            button_name="Raw",
            render=render_raw,
        ),
        Page(
            title=f"Real vs. Pauseless Speed - Race #{race_number:,}",
            description=description,
            fields=real_speed_fields(race),
            button_name="Pauseless",
            render=render_pauseless,
            default=ctx.invoked_with in ["pauseless", "p"],
        ),
    ]

    message = Message(
        ctx, user, pages,
        url=urls.replay(username, race_number, universe, stats["disqualified"]),
        footer="Adjusted speed recalculated to account for lag at the start of the race" * race["distributed"],
        profile=stats,
        universe=universe,
    )

    await message.send()

    recent.update_recent(ctx.channel.id, race["text_id"])


async def setup(bot):
    await bot.add_cog(RawComparison(bot))
