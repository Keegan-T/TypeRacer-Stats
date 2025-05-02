from datetime import datetime, timezone

from discord.ext import commands

from database import users, races
from database.bot_users import get_user
from graphs import clock_graph, bar_graph
from utils import errors, embeds, strings, dates
from utils.embeds import GraphPage, is_embed

command = {
    "name": "activity",
    "aliases": ["act", "clock"],
    "description": "Displays your daily and weekly active typing periods",
    "parameters": "[username]",
    "usages": ["activity keegant", "activity me week"],
}


class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def activity(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, timeframe = result
        await run(ctx, user, username, timeframe)


def get_args(user, args, info):
    params = f"username timeframe:day|week"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, timeframe):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    race_list = await races.get_races(
        username, columns=["timestamp"], universe=universe,
        start_date=user["start_date"], end_date=user["end_date"]
    )

    daily = [0] * 24
    weekly = [0] * 7

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

    def hour_timestamp(hour):
        return strings.discord_timestamp(
            dates.now().replace(hour=hour, minute=0, second=0, microsecond=0).timestamp(), "t"
        )

    def daily_activity_description(index):
        hours = (hour_timestamp(index % 24), hour_timestamp((index + 1) % 24))
        return (
            f"{hours[0]} - {hours[1]}\n"
            f"{daily[index]:,} / {race_count:,} races ({(daily[index] / race_count) * 100:,.2f}%)"
        )

    def weekly_activity_description(index):
        day = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][index]
        return (
            f"{day}\n"
            f"{weekly[index]:,} / {race_count:,} races ({(weekly[index] / race_count) * 100:,.2f}%)"
        )

    daily_description = (
        f"**Most Active:** {daily_activity_description(daily_max_index)}\n\n"
        f"**Least Active:** {daily_activity_description(daily_min_index)}"
    )
    weekly_description = (
        f"**Most Active:** {weekly_activity_description(weekly_max_index)}\n\n"
        f"**Least Active:** {weekly_activity_description(weekly_min_index)}"
    )

    def render_daily(file_name):
        return clock_graph.render(user, username, daily, file_name, universe)

    def render_weekly(file_name):
        return bar_graph.render(user, username, weekly, file_name, universe)

    pages = [
        GraphPage(
            render_daily, f"typing_activity_daily_{username}.png",
            "Daily Typing Activity", daily_description, "Daily",
            timeframe == "day",
        ),
        GraphPage(
            render_weekly, f"typing_activity_weekly_{username}.png",
            "Weekly Typing Activity", weekly_description, "Weekly",
            timeframe == "week",
        )
    ]

    message = embeds.GraphMessage(
        ctx=ctx,
        pages=pages,
        user=user,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Activity(bot))
