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
import commands.locks as locks
from commands.basic.realspeedaverage import command_in_use
from database.texts import get_disabled_text_ids

command = {
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
}


class RaceLine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def raceline(self, ctx, *args):
        if locks.line_lock.locked():
            return await ctx.send(embed=command_in_use())

        async with locks.line_lock:
            user = get_user(ctx)

            result = get_args(user, args, command)
            if utils.is_embed(result):
                return await ctx.send(embed=result)

            usernames, start_date, end_date = result
            await run(ctx, user, usernames, start_date, end_date)


def get_args(user, args, info):
    args = [arg.lower() for arg in args]
    username = user["username"]
    start_date = datetime.fromtimestamp(0, timezone.utc)
    end_date = datetime.now(timezone.utc)

    if len(args) < 2:
        if not args or args[0] == "me":
            if not username:
                return errors.missing_argument(info)
            usernames = [username]
        else:
            usernames = [args[0]]

    else:
        usernames = list(args)

        try:
            start_date = utils.floor_day(parser.parse(usernames[0]))
            usernames = usernames[1:]
        except ValueError:
            pass

        try:
            end_date = utils.floor_day(parser.parse(usernames[-1]))
            usernames = usernames[:-1]
        except ValueError:
            pass

    if username:
        usernames = [username if name == "me" else name for name in usernames]

    unique_usernames = []
    for username in usernames:
        if not users.get_user(username):
            return errors.import_required(username)
        if username not in unique_usernames:
            unique_usernames.append(username)

    return unique_usernames, start_date, end_date


async def get_lines(usernames, start_date, end_date, column="number"):
    lines = []
    min_timestamp = float("inf")
    columns = [column, "timestamp"]
    disabled_text_ids = get_disabled_text_ids()
    for username in usernames:
        race_list = await races.get_races(
            username, columns=columns, start_time=start_date.timestamp(), end_time=end_date.timestamp())
        race_list.sort(key=lambda r: r[1])
        if len(race_list) < 2:
            continue
        x, y = [race_list[0][1]], [0]
        race_count = race_list[-1][0]
        point_count = 0
        unique_texts = set()

        for i, race in enumerate(race_list):
            text_id, timestamp = race
            if timestamp < min_timestamp:
                min_timestamp = timestamp

            x.append(timestamp)

            if column == "number":
                y.append(race[0] - race_list[0][0] + 1)
            elif column == "points":
                y.append(point_count)
                point_count += race[0]
            else:
                y.append(len(unique_texts))
                if text_id not in disabled_text_ids:
                    unique_texts.add(text_id)

        max_value = race_count
        if column == "points":
            max_value = point_count
        elif column == "text_id":
            max_value = len(unique_texts)

        lines.append((username, x, y, max_value, min_timestamp))

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


async def run(ctx, user, usernames, start_date, end_date, column="number"):
    lines = await get_lines(usernames, start_date, end_date, column)

    if not lines:
        return await ctx.send(embed=no_data())

    kind = "Races"
    if column == "points":
        kind = "Points"
    elif column == "text_id":
        kind = "Texts Typed"
    title = f"{kind} Over Time"
    if len(lines) == 1:
        title += f" - {lines[0][0]}"

    start_time = start_date.timestamp()
    if start_time > 0:
        title += f"\n{utils.get_display_date_range(start_date, end_date)}"
    elif datetime.now(timezone.utc).date() != end_date.date():
        title += f"\n{utils.get_display_date_range(datetime.fromtimestamp(lines[0][4], tz=timezone.utc), end_date)}"

    lines.sort(key=lambda x: x[3], reverse=True)

    file_name = f"{kind.lower()}_over_time_{usernames[0]}.png"
    graphs.line(user, lines, title, "Date", kind, file_name)

    file = File(file_name, filename=file_name)
    await ctx.send(file=file)

    utils.remove_file(file_name)


def too_many_usernames():
    return Embed(
        title="Too Many Usernames",
        description="Can only plot up to 10 usernames at once",
        color=colors.error,
    )


def no_data():
    return Embed(
        title="Not Enough Data",
        description="At least one user has no races in this range",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(RaceLine(bot))
