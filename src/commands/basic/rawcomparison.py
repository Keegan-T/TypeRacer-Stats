from discord.ext import commands

import commands.recent as recent
from api.races import get_race
from api.users import get_stats
from commands.basic.realspeed import get_args
from config import prefix
from database.bot.users import get_user
from graphs import match_graph
from utils import errors, urls, strings
from utils.embeds import Page, Message, is_embed

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
        "rawcomparison https://data.typeracer.com/pit/result?id=|tr:keegant|1000000",
    ],
}


class RawComparison(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def rawcomparison(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, universe)


async def run(ctx, user, username, race_number, universe):
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    elif race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race(username, race_number, get_typos=True, universe=universe)
    if not race_info or "unlagged" not in race_info:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))

    description = strings.text_description(race_info) + "\n\n"
    description += strings.real_speed_description(race_info)
    description += strings.raw_speed_description(race_info)
    description += "Completed " + strings.discord_timestamp(race_info["timestamp"])

    graph_title = f"Race Graph - {username} - Race #{race_number:,}"
    y_label = "Adjusted vs. Raw WPM"
    adjusted_ranking = {
        "username": "Adjusted",
        "keystroke_wpm": race_info["keystroke_wpm_adjusted"],
    }

    def render_raw():
        rankings = [
            {
                "username": "Raw Adjusted",
                "keystroke_wpm": race_info["keystroke_wpm_raw_adjusted"],
            },
            adjusted_ranking
        ]

        return match_graph.render(
            user, rankings, graph_title, y_label, universe,
            markers=[race_info["typos"], []]
        )

    def render_pauseless():
        rankings = [
            {
                "username": "Pauseless",
                "keystroke_wpm": race_info["keystroke_wpm_pauseless_adjusted"],
            },
            adjusted_ranking,
        ]

        return match_graph.render(
            user, rankings, graph_title, y_label, universe,
            markers=[race_info["typos"], race_info["pauses"]]
        )

    pages = [
        Page(
            title=f"Real vs. Raw Speed - Race #{race_number:,}",
            description=description,
            button_name="Raw",
            render=render_raw,
        ),
        Page(
            title=f"Real vs. Pauseless Speed - Race #{race_number:,}",
            description=description,
            button_name="Pauseless",
            render=render_pauseless,
            default=ctx.invoked_with in ["pauseless", "p"],
        ),
    ]

    message = Message(
        ctx, user, pages,
        url=urls.replay(username, race_number, universe, stats["disqualified"]),
        footer="Adjusted speed recalculated to account for lag at the start of the race" * race_info["distributed"],
        profile=stats,
        universe=universe,
    )

    await message.send()

    recent.text_id = race_info["text_id"]


async def setup(bot):
    await bot.add_cog(RawComparison(bot))
