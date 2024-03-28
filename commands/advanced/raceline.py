from discord import Embed, File
from discord.ext import commands
from datetime import datetime, timezone
from dateutil import parser
import graphs
import utils
import errors
import colors
from database.bot_users import get_user
import database.races as races
import database.users as users
import os
import commands.locks as locks
from commands.basic.realspeedaverage import command_in_use

info = {
    "name": "raceline",
    "aliases": ["rl"],
    "description": "Displays a graph of user's races over time",
    "parameters": "<date> [username] <username_2> ... <username_10> <date>",
    "usages": [
        "raceline keegant",
        "raceline 2022-04-20 keegant",
        "raceline 4/20/22 keegant 1/1/24",
        "raceline keegant mark40511 charlieog wordracer888 deroche1",
    ],
    "import": True,
}


class RaceLine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def raceline(self, ctx, *params):
        if locks.line_lock.locked():
            return await ctx.send(embed=command_in_use())

        async with locks.line_lock:
            user = get_user(ctx)
            try:
                usernames, start_date, end_date = await get_params(ctx, user, params)
            except ValueError:
                return

            await run(ctx, user, usernames, start_date, end_date)


async def get_params(ctx, user, params, command=info):
    usernames = []
    start_date = datetime.fromtimestamp(0, timezone.utc)
    end_date = datetime.now(timezone.utc)

    if len(params) < 2:
        if not params or params[0].lower() == "me":
            username = user["username"]
            if not username:
                await ctx.send(embed=errors.missing_param(command))
                raise ValueError
        else:
            username = params[0]

        usernames = [username]

    elif len(params) > 1:
        usernames = list(params)

        try:
            start_date = utils.floor_day(parser.parse(params[0]))
            usernames = usernames[1:]
        except ValueError:
            pass

        try:
            end_date = utils.floor_day(parser.parse(params[-1]))
            usernames = usernames[:-1]
        except ValueError:
            pass

    if user["username"]:
        for i in range(len(usernames)):
            if usernames[i] == "me":
                usernames[i] = user["username"]

    unique_usernames = []
    for username in usernames:
        username = username.lower()
        if not users.get_user(username):
            await ctx.send(embed=errors.import_required(username))
            raise ValueError
        if username not in unique_usernames:
            unique_usernames.append(username)

    return unique_usernames, start_date, end_date


async def get_lines(usernames, start_date, end_date, points=False):
    lines = []
    min_timestamp = float("inf")
    columns = ["points" if points else "number", "timestamp"]
    for username in usernames:
        race_list = await races.get_races(
            username, columns=columns, start_time=start_date.timestamp(), end_time=end_date.timestamp())
        race_list.sort(key=lambda r: r[1])
        if len(race_list) < 2:
            continue
        x, y = [race_list[0][1]], [0]
        race_count = race_list[-1][0]
        point_count = 0
        for i, race in enumerate(race_list):
            timestamp = race[1]
            if timestamp < min_timestamp:
                min_timestamp = timestamp

            x.append(timestamp)
            if points:
                y.append(point_count)
                point_count += race[0]
            else:
                y.append(race[0] - race_list[0][0] + 1)

        lines.append((username, x, y, point_count if points else race_count, min_timestamp))

    if len(lines) == 0:
        return lines

    # Extending all lines to the end of the graph
    max_timestamp = end_date.timestamp()
    for line in lines:
        end_timestamp = line[1][-1]
        end_number = line[2][-1]
        if end_timestamp < max_timestamp:
            line[1].append(max_timestamp)
            line[2].append(end_number)

    return lines


async def run(ctx, user, usernames, start_date, end_date, points=False):
    lines = await get_lines(usernames, start_date, end_date, points)

    if not lines:
        return await ctx.send(embed=no_data())

    kind = "Points" if points else "Races"
    title = f"{kind} Over Time"
    if len(lines) == 1:
        title += f" - {lines[0][0]}"

    start_time = start_date.timestamp()
    if start_time > 0:
        title += f"\n{utils.get_display_date_range(start_date, end_date)}"
    elif datetime.now(timezone.utc).date() != end_date.date():
        title += f"\n{utils.get_display_date_range(datetime.fromtimestamp(lines[0][5], tz=timezone.utc), end_date)}"

    lines.sort(key=lambda x: x[3], reverse=True)

    file_name = f"{kind.lower()}_over_time_{usernames[0]}.png"
    graphs.line(user, lines, title, "Date", kind, file_name)

    file = File(file_name, filename=file_name)
    await ctx.send(file=file)

    os.remove(file_name)


def too_many_usernames():
    return Embed(
        title="Too Many Usernames",
        description="Can only plot up to 10 usernames at once",
        color=colors.error,
    )


def no_data():
    return Embed(
        title="No Data",
        description="Given users have no data in the specified range",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(RaceLine(bot))
