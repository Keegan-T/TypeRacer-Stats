from discord import Embed
from discord.ext import commands
import utils
import errors
import colors
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from database.bot_users import get_user
import database.users as users
import database.races as races
import database.texts as texts

command = {
    "name": "races",
    "aliases": ["racedetails", "rd"],
    "description": "Displays a user's race stats within a timeframe",
    "parameters": "[username] <start_date/start_number> <end_date/end_number>",
    "defaults": {
        "start_date": "the user's account creation date",
        "end_date": "today",
        "start_number": 1,
        "end_number": "the user's most recent race number",
    },
    "usages": [
        "races keegant",
        "races keegant 2022-04-20 2023-04-20",
        "races keegant 800k 900k",
    ],
}


class Races(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def races(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, start_date, end_date, start_number, end_number = result
        await run(ctx, user, username, start_date, end_date, start_number, end_number)


def get_args(user, args, info):
    start_date = None
    end_date = None
    start_number = None
    end_number = None

    if len(args) > 1 and args[1]:
        params = "username category:day|week|month|year"
        result = utils.parse_command(user, params, args, info)
        if not utils.is_embed(result):
            username, date = result
            now = utils.now()
            if date == "day":
                start_date = utils.floor_day(now)
                end_date = start_date + relativedelta(days=1)
            elif date == "week":
                start_date = utils.floor_week(now)
                end_date = start_date + relativedelta(weeks=1)
            elif date == "month":
                start_date = utils.floor_month(now)
                end_date = start_date + relativedelta(months=1)
            elif date == "year":
                start_date = utils.floor_year(now)
                end_date = start_date + relativedelta(years=1)

            end_date -= relativedelta(microseconds=1)

            return username, start_date, end_date, start_number, end_number

    params = "username int int"
    result = utils.parse_command(user, params, args, info)

    if utils.is_embed(result):
        params = "username date date"
        result = utils.parse_command(user, params, args, info)

        if utils.is_embed(result):
            return result

        username, start_date, end_date = result

        if start_date:
            start_date = utils.floor_day(start_date)

        if end_date:
            end_date = utils.floor_day(end_date)

        if start_date and end_date and start_date > end_date:
            start_date, end_date = end_date, start_date

    else:
        username, start_number, end_number = result

        if (isinstance(start_number, int) and start_number < 1 or
                isinstance(end_number, int) and end_number < 1):
            return errors.greater_than(0)

        if start_number and end_number and start_number > end_number:
            start_number, end_number = end_number, start_number

    return username, start_date, end_date, start_number, end_number


async def run(ctx, user, username, start_date, end_date, start_number, end_number):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    if start_number and not end_number:
        end_number = stats["races"]

    if start_date and not end_date:
        end_date = datetime.now(timezone.utc)

    title = "Race Stats - "
    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    if start_date is None and start_number is None:
        title += "All-Time"
        start = stats["joined"]
        end = datetime.now(timezone.utc).timestamp()
        race_list = await races.get_races(username, columns, start, end)
        if not race_list:
            return await ctx.send(embed=errors.no_races_in_range())

    elif start_date is None:
        end_number = min(end_number, stats["races"])
        title += f"Races {start_number:,} - {end_number:,}"
        race_list = await races.get_races(username, columns, start_number=start_number, end_number=end_number)
        if not race_list:
            return await ctx.send(embed=errors.no_races_in_range())
        start = race_list[0][7]
        end = race_list[-1][7] + 0.01

    else:
        start = start_date.timestamp()
        if start < stats["joined"]:
            start = stats["joined"]
            start_date = datetime.utcfromtimestamp(stats["joined"])
        end = end_date.timestamp()
        title += utils.get_display_date_range(start_date, end_date)
        race_list = await races.get_races(username, columns, start_date.timestamp(), end_date.timestamp())
        if not race_list:
            return await ctx.send(embed=errors.no_races_in_range())

    race_list.sort(key=lambda x: x[7])

    embed = Embed(title=title, color=user["colors"]["embed"])
    if len(race_list) == 0:
        embed.description = "No races completed"
        return await ctx.send(embed=embed)

    utils.add_profile(embed, stats)
    add_stats(embed, username, race_list, start, end)

    await ctx.send(embed=embed)


def add_stats(embed, username, race_list, start, end, mini=False):
    end = min(end, datetime.now(timezone.utc).timestamp())

    text_list = texts.get_texts(as_dictionary=True)

    race_count = len(race_list)
    wins = 0
    points = 0
    total_wpm = 0
    total_accuracy = 0
    best_last_10 = 0
    current_last_10 = 0
    words = 0
    characters = 0
    seconds = 0
    unique_texts = set()
    best_race = {"wpm": 0}
    worst_race = {"wpm": 7200000}
    first_race = race_list[0]
    last_race = race_list[-1]
    race_difference = last_race[1] - first_race[1] + 1
    seconds_elapsed = last_race[7] - first_race[7]
    days = utils.count_unique_dates(start, end - 0.001)
    longest_break = {"time": 0, "start_race": {}, "end_race": {}}

    for i, race in enumerate(race_list):
        if race[6] > 1 and race[5] == 1:
            wins += 1
        points += race[4]
        wpm = race[2]
        total_wpm += wpm
        total_accuracy += race[3]
        quote = text_list[race[0]]["quote"]

        current_last_10 += wpm
        if i >= 9:
            if current_last_10 > best_last_10:
                best_last_10 = current_last_10
            current_last_10 -= race_list[i - 9][2]

        words += len(quote.split(" "))
        characters += len(quote)
        seconds += utils.calculate_seconds(quote, wpm)
        unique_texts.add(race[0])
        if wpm > best_race["wpm"]:
            best_race = race
        if wpm < worst_race["wpm"]:
            worst_race = race
        previous_race = race_list[i - 1]
        break_time = race[7] - previous_race[7]
        if break_time > longest_break["time"]:
            longest_break = {
                "time": break_time,
                "start_race": {"timestamp": previous_race[7], "number": previous_race[1]},
                "end_race": {"timestamp": race[7], "number": race[1]},
            }

    average_wpm = total_wpm / race_count
    accuracy_percent = (total_accuracy / race_count) * 100
    points_per_race = points / race_count
    win_percent = (wins / race_count) * 100
    words_per_race = words / race_count
    characters_per_race = characters / race_count
    seconds_per_race = seconds / race_count
    text_count = len(unique_texts)

    summary_string = (
        f"**Average Speed:** {average_wpm:,.2f} WPM ([{worst_race['wpm']:,.2f}]"
        f"(https://data.typeracer.com/pit/result?id=play|tr:{username}|{worst_race['number']}) - "
        f"[{best_race['wpm']:,.2f}]"
        f"(https://data.typeracer.com/pit/result?id=play|tr:{username}|{best_race['number']}))\n"
        f"**Races:** {race_count:,} ({accuracy_percent:.2f}% Accuracy)\n"
        f"**Wins:** {wins:,} ({win_percent:.2f}%)\n"
        f"**Points:** {points:,.0f} ({points_per_race:,.2f} points/race)"
    )

    if len(race_list) > 10 and not mini:
        summary_string += f"\n**Best Last 10:** {best_last_10 / 10:,.2f} WPM"

    embed.add_field(
        name="Summary",
        value=summary_string,
        inline=False,
    )

    if mini:
        return

    details = (
        f"**Words Typed:** {words:,} ({words_per_race:,.2f} words/race)\n"
        f"**Characters Typed:** {characters:,} ({characters_per_race:,.2f} chars/race)\n"
        f"**Race Time:** {utils.format_duration_short(seconds)} ({seconds_per_race:,.2f}s/race)\n"
        f"**Time Difference:** {utils.format_duration_short(seconds_elapsed)}\n"  # Race Timespan, Time Elapsed, Time Difference
        f"**Unique Texts:** {text_count:,}\n\n"
    )

    other_stats = (
        f"**Race:** [#{first_race[1]:,}]"
        f"(https://data.typeracer.com/pit/result?id=|tr:{username}|{first_race[1]}) - "
        f"<t:{int(first_race[7])}>"
    )

    if len(race_list) > 1:
        other_stats = (
            f"**First Race:** [#{first_race[1]:,}]"
            f"(https://data.typeracer.com/pit/result?id=|tr:{username}|{first_race[1]}) - "
            f"<t:{int(first_race[7])}>\n"
            f"**Last Race:** [#{last_race[1]:,}]"
            f"(https://data.typeracer.com/pit/result?id=|tr:{username}|{last_race[1]}) - "
            f"<t:{int(last_race[7])}>\n"
            f"**Longest Break:** {utils.format_duration_short(longest_break['time'])}"
            f" (Starting on Race [#{longest_break['start_race']['number']:,}]"
            f"(https://data.typeracer.com/pit/result?id=|tr:{username}|{longest_break['start_race']['number']}))\n"
            f"<t:{int(longest_break['start_race']['timestamp'])}> - <t:{int(longest_break['end_race']['timestamp'])}>"
        )

    if days > 1:
        embed.add_field(name="Details", value=details, inline=False)

        daily_races = race_count / days
        daily_points = points / days
        daily_seconds = seconds / days

        embed.add_field(
            name=f"Daily Average (Over {days:,} Days)",
            value=f"**Races:** {daily_races:,.2f}\n"
                  f"**Points:** {daily_points:,.2f}\n"
                  f"**Time:** {utils.format_duration_short(daily_seconds)}\n\n"
                  f"{other_stats}",
            inline=False,
        )

    else:
        embed.add_field(name="Details", value=details + other_stats, inline=False)

    if race_difference > len(race_list):
        embed.set_footer(text=f"Missing races found in this range, actual races completed: {race_difference:,}")


def same_dates():
    return Embed(
        title="Invalid Date Range",
        description="Dates cannot be the same",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Races(bot))
