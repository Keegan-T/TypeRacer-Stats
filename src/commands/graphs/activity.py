import re
from datetime import datetime, timezone

from discord.ext import commands

from commands.stats.stats import get_args
from config import prefix
from database.main import races, users
from database.bot.users import get_user
from graphs import clock_graph, bar_graph
from utils import errors, strings, dates
from utils.embeds import Page, Message, is_embed

command = {
    "name": "activity",
    "aliases": ["act", "clock", "clock*"],
    "description": "Displays your daily and weekly active typing periods\n"
                   f"Use `{prefix}activity me utc-[offset]` to set the timezone offset\n"
                   f"Use `{prefix}clock*` to see the exact amount of races for each time period",
    "parameters": "[username]",
    "usages": ["activity"],
}


class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def activity(self, ctx, *args):
        user = get_user(ctx)
        args, user = dates.set_command_date_range(args, user)
        offset = 0
        if len(args) > 1 and re.match(r"^utc[+-](?:[0-9]|1[0-2]|2[0-3])$", args[1].lower()):
            offset = int(args[1][3:])

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username, offset)


async def run(ctx, user, username, offset):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    race_list = await races.get_races(
        username, columns=["timestamp"], universe=universe,
        start_date=user["start_date"], end_date=user["end_date"],
        text_pool=user["settings"]["text_pool"],
    )
    if not race_list:
        return await ctx.send(embed=errors.no_races_in_range(universe))

    daily = [0] * 24
    weekly = [0] * 7
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    for race in race_list:
        dt = datetime.fromtimestamp(race["timestamp"], timezone.utc)
        hour = dt.hour
        day = (dt.weekday() + 1) % 7
        daily[hour] += 1
        weekly[day] += 1

    race_count = len(race_list)
    daily_max_index = daily.index(max(daily))
    daily_min_index = daily.index(min(daily))
    weekly_max_index = weekly.index(max(weekly))
    weekly_min_index = weekly.index(min(weekly))

    def timestamp_range(hour):
        timestamp = lambda h: strings.discord_timestamp(
            dates.now().replace(hour=h, minute=0, second=0, microsecond=0).timestamp(), "t"
        )

        return timestamp(hour) + " - " + timestamp((hour + 1) % 24)

    def daily_activity_description(index):
        return f"{timestamp_range(index)}\n{daily[index]:,} races ({daily[index] / race_count:.2%})"

    def weekly_activity_description(index):
        return f"{days[index]}\n{weekly[index]:,} races ({weekly[index] / race_count:.2%})"

    if ctx.invoked_with == "clock*":
        daily_description = (
            f"**Races:** {race_count:,}\n" + "\n".join(
                f"{timestamp_range(index)}: {daily[index]:,} races ({daily[index] / race_count:.2%})"
                for i in range(24)
                for index in [(i - offset) % 24]
            )
        )

        weekly_description = (
            f"**Races:** {race_count:,}\n" + "\n".join(
                f"**{days[index]}:** {weekly[index]:,} races ({weekly[index] / race_count:.2%})"
                for index in range(0, 7)
            )
        )

    else:
        daily_description = (
            f"**Races:** {race_count:,}\n\n"
            f"**Most Active:** {daily_activity_description(daily_max_index)}\n\n"
            f"**Least Active:** {daily_activity_description(daily_min_index)}"
        )
        weekly_description = (
            f"**Races:** {race_count:,}\n\n"
            f"**Most Active:** {weekly_activity_description(weekly_max_index)}\n\n"
            f"**Least Active:** {weekly_activity_description(weekly_min_index)}"
        )

    pages = [
        Page(
            title="Daily Typing Activity",
            description=daily_description,
            button_name="Daily",
            render=lambda: clock_graph.render(user, username, daily, universe, offset),
        ),
        Page(
            title="Weekly Typing Activity",
            description=weekly_description,
            button_name="Weekly",
            render=lambda: bar_graph.render(user, username, weekly, universe),
        )
    ]

    message = Message(
        ctx=ctx,
        pages=pages,
        user=user,
        profile=stats,
        universe=universe,
        text_pool=user["settings"]["text_pool"],
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Activity(bot))
