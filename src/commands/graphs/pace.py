from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from discord.ext import commands

from commands.races.milestone import run as run_milestone
from database.main import races, users
from database.bot.users import get_user
from graphs import line_graph
from utils import errors, strings, dates
from utils.embeds import Page, is_embed, Message

periods = ["month", "day", "week", "year", "all"]
command = {
    "name": "pace",
    "aliases": [],
    "description": "Displays an estimate of when a user will achieve a milestone\n"
                   "`daily_rate` accepts day/week/month/year for those averages",
    "parameters": "[username] <number> <category> <daily_rate>",
    "defaults": {
        "number": "the user's next milestone",
        "category": "races",
        "daily_rate": "daily average of the last 30 days"
    },
    "usages": [
        "pace keegant",
        "pace keegant 2m races",
        "pace ginoo75 200k races 100",
        "pace clergy 10m points day",
    ],
}


class Pace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def pace(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, number, category, rate = result
        await run(ctx, user, username, number, category, rate)


def get_args(user, args, info):
    # -pace username1 username2 milestone category rate1 rate2
    # -pace username1 username2 rate1 rate2
    if len(args) == 4 and args[-1] in periods:
        params = f"username number category:races|points period:{'|'.join(periods)}"
    else:
        params = "username number category:races|points number"

    result = strings.parse_command(user, params, args, info)
    if is_embed(result):
        return result

    return result


async def run(ctx, user, username, number, category, rate):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    race_list = await races.get_races(
        username, ["number", "points", "timestamp"],
        user["start_date"], user["end_date"], universe=universe,
    )
    race_list.sort(key=lambda x: x["timestamp"])

    column = "number" if category == "races" else "points"
    cumulative_race_list = []
    timestamps = []
    values = []
    cumulative_points = 0
    current = 0
    for i in range(len(race_list)):
        num, points, timestamp = race_list[i]
        cumulative_points += points
        cumulative_race = {
            "number": num,
            "points": cumulative_points,
            "timestamp": timestamp,
        }
        cumulative_race_list.append(cumulative_race)
        timestamps.append(timestamp)
        value = cumulative_race[column]
        values.append(value)
        if value > current:
            current = value

    if not number:
        number = next_milestone(current)
    if number <= current:
        await ctx.send(content="User has already achieved this milestone:")
        return await run_milestone(ctx, user, username, number, category)

    if not rate:
        rate = "month"
    average_of = ""
    if isinstance(rate, str):
        if rate == "all":
            average_of = f"\n(Average of all-time)"
        else:
            average_of = f"\n(Average of last {rate})"
    if rate in periods:
        end_date = dates.now()
        date_range = {
            "day": relativedelta(days=1),
            "week": relativedelta(weeks=1),
            "month": relativedelta(months=1),
            "year": relativedelta(years=1),
        }.get(rate, None)
        if not date_range:
            start_date = datetime.fromtimestamp(min(timestamps), tz=timezone.utc)
        else:
            start_date = end_date - date_range

        rate_list = [
            race for race in cumulative_race_list
            if start_date.timestamp() <= race["timestamp"] <= end_date.timestamp()
        ]
        numerator = 0
        if rate_list:
            numerator = max(race[column] for race in rate_list) - min(race[column] for race in rate_list)
        denominator = (end_date.timestamp() - start_date.timestamp()) / 86400
        rate = numerator / denominator

    render = None
    completion = "Never"
    remaining = number - current
    days_left = remaining / rate if rate > 0 else float("inf")
    if days_left < 365 * 3000 - dates.now().year:
        predicted_timestamp = dates.now().timestamp() + (days_left * 86400)
        completion = strings.discord_timestamp(predicted_timestamp)

        timestamps.append(predicted_timestamp)
        values.append(number)

        render = lambda: line_graph.render(
            user, [[username, timestamps, values]],
            f"Races Over Time Projection - {username}",
            "Date", "Races"
        )

    category = category.title()
    page = Page(
        title=f"Pace Calculator ({category})",
        description=(
            f"**Current {category}:** {current:,.0f}\n"
            f"**Target {category}:** {number:,.0f}\n"
            f"**Rate:** {rate:,.2f} / Day{average_of}\n"
            f"**Estimated Completion:** {completion}"
        ),
        render=render,
    )

    message = Message(
        ctx=ctx,
        user=user,
        pages=page,
        profile=stats,
        universe=universe,
    )

    await message.send()


def next_milestone(n):
    for i in [50, 100, 500, 1000, 5000, 10000]:
        if n < i:
            return i
    if n < 100000:
        return ((n // 10000) + 1) * 10000
    else:
        return ((n // 100000) + 1) * 100000


async def setup(bot):
    await bot.add_cog(Pace(bot))
