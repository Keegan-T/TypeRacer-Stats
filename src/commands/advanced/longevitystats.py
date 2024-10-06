from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from discord import Embed
from discord.ext import commands

import database.races as races
import database.users as users
from database.bot_users import get_user
from utils import errors, strings, dates, embeds

periods = ["month", "day", "week", "year"]
command = {
    "name": "longevitystats",
    "aliases": ["ginoo75", "ginoo", "wellknown", "ls"],
    "description": "Displays the number of times a user has completed n races in a time period",
    "parameters": "[username] <n> <period>",
    "defaults": {
        "n": 1000,
        "period": "month",
    },
    "usages": [
        "longevitystats ginoo75",
        "longevitystats mark40511 1",
        "longevitystats keegant 1k day"
    ],
}


class LongevityStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def longevitystats(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, n, period = result
        await run(ctx, user, username, n, period)


def get_args(user, args, info):
    params = f"username int:1000 period:{'|'.join(periods)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, n, time_period):
    if n < 1:
        return await ctx.send(embed=errors.greater_than(0))

    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    all_history = await get_history(username, time_period, universe, user["start_date"], user["end_date"])
    history = [period for period in all_history if period[2] >= n]
    over = len(history)

    # streak, start date, end date
    current_streak = [0, 0, 0]
    best_streak = [0, 0, 0]

    for i in range(len(history)):
        period = history[i]
        prev_period = history[i - 1]

        if period[0] == prev_period[1]:
            current_streak = [current_streak[0] + 1, current_streak[1], period[0]]

        else:
            current_streak = [1, period[0], period[0]]

        if current_streak[0] > best_streak[0]:
            best_streak = current_streak

    if best_streak[0] == 0:
        description = f"User has not achieved this many races in a {time_period}"

    else:
        best_streak_range = get_streak_string(best_streak[1], best_streak[2], time_period)

        description = f"**Best Streak:** {best_streak[0]:,} ({best_streak_range})\n"

        streak_end = current_streak[2]
        if time_period == "day":
            now = dates.floor_day(dates.now())
            previous = now - relativedelta(days=1)
        elif time_period == "week":
            now = dates.floor_week(dates.now())
            previous = now - relativedelta(days=7)
        elif time_period == "month":
            now = dates.floor_month(dates.now())
            previous = now - relativedelta(months=1)
        else:
            now = dates.floor_year(dates.now())
            previous = now - relativedelta(years=1)

        if streak_end == now.timestamp() or streak_end == previous.timestamp():
            current_streak_range = get_streak_string(current_streak[1], current_streak[2], time_period)
            description += f"**Current Streak:** {current_streak[0]:,} ({current_streak_range})\n"
        else:
            description += f"**Current Streak:** 0\n"

        description += f"**Total {time_period.title()}s:** {over:,}"

    embed = Embed(
        title=f"Longevity Stats - {time_period.title()}s ({n:,} Races)",
        description=description,
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)


async def get_history(username, kind, universe, start_date, end_date):
    race_list = await races.get_races(
        username, columns=["timestamp"], universe=universe, start_date=start_date, end_date=end_date
    )
    race_list.sort(key=lambda x: x[0])

    history = []
    for race in race_list:
        timestamp = race[0]

        if len(history) == 0 or timestamp > history[-1][1]:
            if kind == "day":
                start = dates.floor_day(datetime.fromtimestamp(timestamp, tz=timezone.utc))
                end = start.timestamp() + 86400
            elif kind == "week":
                start = dates.floor_week(datetime.fromtimestamp(timestamp, tz=timezone.utc))
                end = start.timestamp() + 86400 * 7
            elif kind == "month":
                start = dates.floor_month(datetime.fromtimestamp(timestamp, tz=timezone.utc))
                end = (start + relativedelta(months=1)).timestamp()
            else:
                start = dates.floor_year(datetime.fromtimestamp(timestamp, tz=timezone.utc))
                end = (start + relativedelta(years=1)).timestamp()

            history.append([start.timestamp(), end, 1])

        else:
            history[-1][2] += 1

    return history


def get_streak_string(start, end, kind):
    streak_start = datetime.fromtimestamp(start, tz=timezone.utc)
    streak_end = datetime.fromtimestamp(end, tz=timezone.utc)
    streak_1 = streak_start == streak_end

    if kind == "day":
        streak_range = strings.get_display_date_range(streak_start, streak_end)

    elif kind == "week":
        streak_range = f"Week of {streak_start.strftime('%#m/%#d/%Y')}"
        if not streak_1:
            streak_range += f" - Week of {streak_end.strftime('%#m/%#d/%Y')}"

    elif kind == "month":
        streak_range = f"{streak_start.strftime('%B %Y')}"
        if not streak_1:
            streak_range += f" - {streak_end.strftime('%B %Y')}"

    else:
        streak_range = f"{streak_start.strftime('%Y')}"
        if not streak_1:
            streak_range += f" - {streak_end.strftime('%Y')}"

    return streak_range


async def setup(bot):
    await bot.add_cog(LongevityStats(bot))
