from datetime import datetime, timezone

from dateutil import parser
from discord import Embed, File
from discord.ext import commands

import commands.locks as locks
import database.main.races as races
import database.main.users as users
from database.bot.users import get_user
from database.main.texts import get_disabled_text_ids
from graphs import line_graph
from utils import errors, colors, strings, dates, embeds, files
from utils.errors import command_in_use

command = {
    "name": "raceline",
    "aliases": ["rl"],
    "description": "Displays a graph of user's races over time",
    "parameters": "[username] <username_2> ... <username_10> <start_date> <end_date>",
    "usages": [
        "raceline keegant",
        "raceline keegant 2022-04-20",
        "raceline keegant 4/20/22 1/1/24",
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
            args, user = dates.set_command_date_range(args, user)

            result = get_args(user, args, command)
            if embeds.is_embed(result):
                return await ctx.send(embed=result)

            await run(ctx, user, result)


def get_args(user, args, info):
    usernames = [arg.lower() for arg in args]
    username = user["username"]
    if not usernames or "me" in usernames:
        if not username:
            return errors.missing_argument(info)

    if not usernames:
        usernames = [username]
    if username:
        usernames = [username if name == "me" else name for name in usernames]

    unique_usernames = []
    for username in usernames:
        username = strings.username_aliases.get(username, username)
        if not users.get_user(username, user["universe"]):
            return errors.import_required(username)
        if username not in unique_usernames:
            unique_usernames.append(username)

    return unique_usernames


async def get_lines(usernames, start_date, end_date, column="number", universe="play", text_pool="all"):
    lines = []
    min_timestamp = float("inf")
    columns = [column, "timestamp"]
    text_bests = column == "text_best_average"
    if text_bests:
        columns = ["text_id", "timestamp", "wpm"]
    disabled_text_ids = get_disabled_text_ids()
    for username in usernames:
        race_list = await races.get_races(
            username, columns=columns, start_date=start_date.timestamp(),
            end_date=end_date.timestamp(), universe=universe,
            text_pool=text_pool,
        )
        race_list.sort(key=lambda r: r["timestamp"])
        if len(race_list) < 2:
            continue
        x, y = [], []
        race_count = race_list[-1][0]
        if text_pool != "all":
            race_count = 1
        point_count = 0
        unique_texts = set()
        max_average = 0
        text_ids = {}
        wpm_total = 0
        wpm_count = 0

        for i, race in enumerate(race_list):
            text_id = race[0]
            timestamp = race[1]
            if timestamp < min_timestamp:
                min_timestamp = timestamp

            if not text_bests:
                x.append(timestamp)

            if column == "number":
                if text_pool == "all":
                    y.append(race[0] - race_list[0][0] + 1)
                else:
                    y.append(i + 2)
            elif column == "points":
                point_count += race[0]
                y.append(point_count)
            elif column == "text_id":
                if text_id not in disabled_text_ids:
                    unique_texts.add(text_id)
                y.append(len(unique_texts))
            else:
                if race[2] in disabled_text_ids:
                    continue
                wpm = race[2]
                if text_ids.get(text_id, False):
                    if wpm > text_ids[text_id]:
                        improvement = wpm - text_ids[text_id]
                        wpm_total += improvement
                        text_ids[text_id] = wpm
                        x.append(timestamp)
                        average = wpm_total / wpm_count
                        if average > max_average:
                            max_average = average
                        y.append(average)
                else:
                    wpm_total += wpm
                    wpm_count += 1
                    text_ids[text_id] = wpm
                    x.append(timestamp)
                    average = wpm_total / wpm_count
                    if average > max_average:
                        max_average = average
                    y.append(average)

        if column == "number":
            max_value = race_count
        elif column == "points":
            max_value = point_count
        elif column == "text_id":
            max_value = len(unique_texts)
        else:
            max_value = max_average

        lines.append((username, x, y, max_value, min_timestamp))

    if len(lines) == 0:
        return lines

    # Extending all lines to the end of the range
    max_timestamp = end_date.timestamp()
    for line in lines:
        end_timestamp = line[1][-1]
        end_number = line[2][-1]
        if end_timestamp < max_timestamp:
            line[1].append(max_timestamp)
            line[2].append(end_number)

    return lines


async def run(ctx, user, usernames, column="number"):
    if len(usernames) > 10:
        return await ctx.send(embed=too_many_usernames())

    universe = user["universe"]
    era_string = strings.get_era_string(user)
    if user["start_date"]:
        start_date = datetime.fromtimestamp(user["start_date"])
    else:
        start_date = datetime.fromtimestamp(0, timezone.utc)
    if user["end_date"]:
        end_date = datetime.fromtimestamp(user["end_date"])
    else:
        end_date = datetime.now(timezone.utc)

    lines = await get_lines(usernames, start_date, end_date, column, universe=universe, text_pool=user["settings"]["text_pool"])

    if not lines:
        return await ctx.send(embed=no_data(universe), content=era_string)

    if column == "number":
        kind = "Races"
    elif column == "points":
        kind = "Points"
    elif column == "text_id":
        kind = "Texts Typed"
    else:
        kind = "Text Best Average"
    title = f"{kind} Over Time"
    if len(lines) == 1:
        title += f" - {lines[0][0]}"

    start_time = start_date.timestamp()
    if start_time > 0:
        title += f"\n{strings.get_display_date_range(start_date, end_date)}"
    elif datetime.now(timezone.utc).date() != end_date.date():
        title += f"\n{strings.get_display_date_range(datetime.fromtimestamp(lines[0][4], tz=timezone.utc), end_date)}"
    if universe != "play":
        separator = " | " if "\n" in title else "\n"
        title += f"{separator}Universe: {universe}"

    lines.sort(key=lambda x: x[3], reverse=True)

    file_name = line_graph.render(user, lines, title, "Date", kind)

    file = File(file_name, filename=file_name)
    await ctx.send(file=file, content=era_string)

    files.remove_file(file_name)


def too_many_usernames():
    return Embed(
        title="Too Many Usernames",
        description="Can only plot up to 10 usernames at once",
        color=colors.error,
    )


def no_data(universe):
    embed = Embed(
        title="Not Enough Data",
        description="At least one user has no races in this range",
        color=colors.error,
    )
    embeds.add_universe(embed, universe)

    return embed


async def setup(bot):
    await bot.add_cog(RaceLine(bot))
