from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from discord.ext import commands

from commands.advanced.compare import same_username
from database import users, races
from database.bot_users import get_user
from graphs import line_graph
from utils import errors, strings, dates
from utils.embeds import Page, Field, Message, is_embed

periods = ["month", "day", "week", "year", "all"]
command = {
    "name": "pacecompare",
    "aliases": ["pc"],
    "description": "Displays an estimate of when one user will pass another\n"
                   "`daily_rate` accepts day/week/month/year for those averages",
    "parameters": "[username] [username2] <category> <daily_rate1> <daily_rate2>",
    "defaults": {
        "category": "races",
        "daily_rate": "daily average of the last 30 days"
    },
    "usages": [
        "pace xanderec charlieog races",
        "pace mark40511 keegant points 20000 5000",
        "pace cappy_11 rektless races month",
    ],
}


class PaceCompare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def pacecompare(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username1, username2, category, *remaining = result
        await run(ctx, user, username1, username2, category, *remaining)


def get_args(user, args, info):
    if len(args) == 5:
        params = f"username username category:races|points number number"
    else:
        params = f"username username category:races|points period:{'|'.join(periods)}"

    result = strings.parse_command(user, params, args, info)
    if is_embed(result):
        return result

    return result


async def run(ctx, user, username1, username2, category, rate1, rate2=None):
    if username1 == username2:
        return await ctx.send(embed=same_username())

    universe = user["universe"]
    for username in [username1, username2]:
        if not users.get_user(username):
            return await ctx.send(embed=errors.import_required(username, universe))

    columns = ["number", "points", "timestamp"]
    column = "number" if category == "races" else "points"
    user_list = [
        {"username": username1, "rate": rate1},
        {"username": username2, "rate": rate2},
    ]
    for i in range(2):
        race_list = await races.get_races(user_list[i]["username"], columns, user["start_date"], user["end_date"])
        race_list.sort(key=lambda x: x["timestamp"])

        cumulative_race_list = []
        timestamps = []
        values = []
        cumulative_points = 0
        current = 0
        for j in range(len(race_list)):
            num, points, timestamp = race_list[j]
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
        user_list[i].update({
            "cumulative_race_list": cumulative_race_list,
            "timestamps": timestamps,
            "values": values,
            "current": current,
        })

    user_list.sort(key=lambda x: x["current"])

    average_of = ""
    if rate1 in periods:
        if rate1 == "all":
            average_of = f"\n(Average of all-time)"
        else:
            average_of = f"\n(Average of last {rate1})"
        end_date = dates.now()
        for i in range(2):
            date_range = {
                "day": relativedelta(days=1),
                "week": relativedelta(weeks=1),
                "month": relativedelta(months=1),
                "year": relativedelta(years=1),
            }.get(rate1)
            if not date_range:
                start_date = datetime.fromtimestamp(min(user_list[i]["timestamps"]), tz=timezone.utc)
            else:
                start_date = end_date - date_range

            rate_list = [
                race for race in user_list[i]["cumulative_race_list"]
                if start_date.timestamp() <= race["timestamp"] <= end_date.timestamp()
            ]
            numerator = 0
            if rate_list:
                numerator = max(race[column] for race in rate_list) - min(race[column] for race in rate_list)
            denominator = (end_date.timestamp() - start_date.timestamp()) / 86400
            rate = numerator / denominator
            user_list[i]["rate"] = rate
    else:
        if user_list[0]["rate"] < user_list[1]["rate"]:
            user_list[0]["rate"], user_list[1]["rate"] = user_list[1]["rate"], user_list[0]["rate"]

    render = None
    user1, user2 = user_list
    current1 = user1["current"]
    current2 = user2["current"]
    rate1 = user1["rate"]
    rate2 = user2["rate"]
    if rate1 == 0 or rate1 < rate2:
        crossover_point = "Never"
    else:
        days_left = (current2 - current1) / (rate1 - rate2)
        intersection_timestamp = dates.now().timestamp() + (days_left * 86400)
        intersection_value = current1 + rate1 * days_left

        crossover_point = (
            f"At {intersection_value:,.0f} {category} "
            f"({strings.discord_timestamp(intersection_timestamp)})"
        )

        if days_left < 365 * 3000 - dates.now().year:
            for i in range(2):
                user_list[i]["timestamps"].append(intersection_timestamp)
                user_list[i]["values"].append(intersection_value)

            lines = []
            for i in range(2):
                lines.append([
                    user_list[i]["username"],
                    user_list[i]["timestamps"],
                    user_list[i]["values"],
                ])
            render = lambda: line_graph.render(
                user, lines,
                f"Races Over Time Projection\n"
                f"{user_list[0]['username']} vs. {user_list[1]['username']}",
                "Date", "Races"
            )

    category = category.title()
    title = f"Pace Comparison ({category})"

    def formatter(user):
        return (
            f"**Current {category}:** {user['current']:,.0f}\n"
            f"**Rate:** {user['rate']:,.2f} / Day{average_of}\n"
        )

    fields = []
    for i in range(2):
        name = ["Chaser", "Leader"][i]
        stats = formatter(user_list[i])
        fields.append(Field(
            name=user_list[i]["username"] + f" - {name}",
            value=stats,
        ))
    fields.append(Field(
        name="Crossover Point",
        value=crossover_point,
        inline=False,
    ))

    page = Page(
        title=title,
        fields=fields,
        render=render,
    )

    message = Message(ctx, user, page)

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
    await bot.add_cog(PaceCompare(bot))
