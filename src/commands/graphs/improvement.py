from discord.ext import commands

import database.main.races as races
import database.main.users as users
import utils.stats
from api.users import get_stats
from commands.account.download import run as download
from commands.races.races import get_args
from commands.locks import LargeQueryLock
from config import prefix
from database.bot.users import get_user
from graphs import improvement_graph
from utils import errors, strings, dates
from utils.embeds import Page, Message, is_embed

command = {
    "name": "improvement",
    "aliases": ["imp", "timeimprovement", "timp"],
    "description": "Displays a graph of a user's WPM over races\n"
                   f"`{prefix}timeimprovement` will graph WPM over time",
    "parameters": "[username] <start_date/start_number> <end_date/end_number>",
    "defaults": {
        "start_date": "the user's account creation date",
        "end_date": "today",
        "start_number": 1,
        "end_number": "the user's most recent race number",
    },
    "usages": [
        "improvement keegant",
        "improvement keegant 2022-04-20 2023-04-20",
        "improvement keegant 800k 900k",
        "improvement poem day",
        "timeimprovement keegant",
    ],
}


class Improvement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def improvement(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, start_date, end_date, start_number, end_number = result
        time = ctx.invoked_with in ["timeimprovement", "timp"]
        await run(ctx, user, username, start_date, end_date, start_number, end_number, time)


async def run(ctx, user, username, start_date, end_date, start_number, end_number, time):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    async with LargeQueryLock(stats["races"] > 100_000):
        api_stats = get_stats(username, universe=universe)
        await download(racer=api_stats, universe=universe)
        if era_string:
            api_stats = await users.time_travel_stats(api_stats, user)

        if start_number and not end_number:
            end_number = api_stats["races"]

        if start_date and not end_date:
            end_date = dates.now()

        start_date, end_date = dates.time_travel_dates(user, start_date, end_date)

        title = "WPM Improvement"
        columns = ["wpm", "timestamp"]
        if start_date is None and start_number is None:
            timeframe = f" (All-Time)"
            title += " - All-Time"
            race_list = await races.get_races(username, columns=columns, universe=universe)

        elif start_date is None:
            end_number = min(end_number, api_stats["races"])
            timeframe = f" {start_number:,} - {end_number:,}"
            title += f" - Races{timeframe}"
            race_list = await races.get_races(
                username, columns=columns, start_number=start_number,
                end_number=end_number, universe=universe
            )

        else:
            timeframe = f" ({strings.get_display_date_range(start_date, end_date)})"
            title += f" - {strings.get_display_date_range(start_date, end_date)}"
            race_list = await races.get_races(
                username, columns=columns, start_date=start_date.timestamp(),
                end_date=end_date.timestamp(), universe=universe
            )

        if era_string:
            race_list = utils.stats.time_travel_races(race_list, user)

        if len(race_list) == 0:
            return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

        race_list.sort(key=lambda x: x[1])
        wpm = []
        timestamps = []
        best = 0
        average = 0
        recent_average = 0
        race_count = len(race_list)
        worst = float("inf")
        moving = min(max(race_count // 15, 1), 500)

        for race in race_list:
            race_wpm = race[0]
            wpm.append(race_wpm)
            timestamps.append(race[1])
            if race_wpm > best:
                best = race_wpm
            if race_wpm < worst:
                worst = race_wpm
            average += race_wpm

        for race in race_list[::-1][:moving]:
            recent_average += race[0]

        average /= race_count
        recent_average /= moving

    description = (
        f"**Races:** {race_count:,}\n"
        f"**Average:** {average:,.2f} WPM\n"
        f"**Best:** {best:,.2f} WPM\n"
        f"**Worst:** {worst:,.2f} WPM\n"
        f"**Average of Last {moving}:** {recent_average:,.2f} WPM"
    )

    pages = [
        Page(
            button_name="Over Races",
            render=lambda: improvement_graph.render(user, wpm, title, timeframe, universe=universe),
            default=time,
        ),
        Page(
            button_name="Over Time",
            render=lambda: improvement_graph.render(user, wpm, title, timeframe, timestamps, universe),
            default=time,
        ),
    ]

    message = Message(
        ctx=ctx,
        user=user,
        pages=pages,
        title=title,
        header=description,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Improvement(bot))
