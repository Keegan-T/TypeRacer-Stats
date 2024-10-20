from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from discord import Embed
from discord.ext import commands

import database.races as races
import database.texts as texts
import database.users as users
from commands.locks import big_lock
from database.bot_users import get_user
from utils import errors, colors, urls, strings, dates, embeds

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
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, start_date, end_date, start_number, end_number = result
        await run(ctx, user, username, start_date, end_date, start_number, end_number)


def get_args(user, args, info):
    start_date = None
    end_date = None
    start_number = None
    end_number = None

    if len(args) > 1 and args[1]:
        params = "username category:day|yesterday|week|month|year"
        result = strings.parse_command(user, params, args, info)
        if not embeds.is_embed(result):
            username, date = result
            now = dates.now()
            if "day" in date:
                start_date = dates.floor_day(now)
                if date == "yesterday":
                    start_date -= relativedelta(days=1)
                end_date = start_date + relativedelta(days=1)
            elif date == "week":
                start_date = dates.floor_week(now)
                end_date = start_date + relativedelta(weeks=1)
            elif date == "month":
                start_date = dates.floor_month(now)
                end_date = start_date + relativedelta(months=1)
            elif date == "year":
                start_date = dates.floor_year(now)
                end_date = start_date + relativedelta(years=1)

            end_date -= relativedelta(microseconds=1)

            return username, start_date, end_date, start_number, end_number

    params = "username int int"
    result = strings.parse_command(user, params, args, info)

    if embeds.is_embed(result):
        params = "username date date"
        result = strings.parse_command(user, params, args, info)

        if embeds.is_embed(result):
            return result

        username, start_date, end_date = result

        if start_date:
            start_date = dates.floor_day(start_date)

        if end_date:
            end_date = dates.floor_day(end_date)

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
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    if stats["races"] > 100_000:
        if big_lock.locked():
            return await ctx.send(embed=errors.large_query_in_progress())
        await big_lock.acquire()

    era_string = strings.get_era_string(user)
    if era_string:
        stats = await users.time_travel_stats(stats, user)

    if start_number and not end_number:
        end_number = stats["races"]

    if start_date and not end_date:
        end_date = dates.now()

    start_date, end_date = dates.time_travel_dates(user, start_date, end_date)
    user_start, user_end = user["start_date"], user["end_date"]

    title = "Race Stats - "
    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    if start_date is None and start_number is None:
        title += "All-Time"
        start = stats["joined"]
        end = dates.now().timestamp()
        if user_start: start = max(start, user_start)
        if user_end: end = min(end, user_end)
        race_list = await races.get_races(username, columns, universe=universe)

    elif start_date is None:
        end_number = min(end_number, stats["races"])
        title += f"Races {start_number:,} - {end_number:,}"
        race_list = await races.get_races(
            username, columns, start_number=start_number,
            end_number=end_number, universe=universe,
            start_date=user_start, end_date=user_end
        )
        if race_list:
            start = race_list[0][7]
            end = race_list[-1][7] + 0.01

    else:
        start = start_date.timestamp()
        if start < stats["joined"]:
            start = stats["joined"]
            start_date = datetime.fromtimestamp(stats["joined"], tz=timezone.utc)
        end = end_date.timestamp()
        title += strings.get_display_date_range(start_date, end_date)
        race_list = await races.get_races(
            username, columns, start_date.timestamp(),
            end_date.timestamp(), universe=universe
        )

    if not race_list:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)
    race_list.sort(key=lambda x: x[7])

    embed = Embed(title=title, color=user["colors"]["embed"])
    embeds.add_profile(embed, stats, universe)
    add_stats(embed, username, race_list, start, end, universe=universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)

    if big_lock.locked():
        big_lock.release()


def add_stats(embed, username, race_list, start, end, mini=False, universe="play"):
    end = min(end, datetime.now(timezone.utc).timestamp())
    text_list = texts.get_texts(as_dictionary=True, universe=universe)

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
    best_race = {}
    worst_race = {}
    best_race_wpm = 0
    worst_race_wpm = 72000000
    first_race = race_list[0]
    last_race = race_list[-1]
    race_difference = last_race[1] - first_race[1] + 1
    seconds_elapsed = last_race[7] - first_race[7]
    days = dates.count_unique_dates(start, end - 0.001)
    longest_break = {"time": 0, "start_race": {}, "end_race": {}}

    previous_race = race_list[0]
    for i, race in enumerate(race_list):
        if race[6] > 1 and race[5] == 1:
            wins += 1

        points += race[4]
        wpm = race[2]
        total_wpm += wpm
        total_accuracy += race[3]

        text_id = race[0]
        text = text_list[text_id]
        quote = text["quote"]

        if "words" not in text:
            text["words"] = len(quote.split(" "))
        if "chars" not in text:
            text["chars"] = len(quote)

        words += text["words"]
        characters += text["chars"]

        current_last_10 += wpm
        if i >= 9:
            if current_last_10 > best_last_10:
                best_last_10 = current_last_10
            current_last_10 -= race_list[i - 9][2]

        seconds += 0 if wpm == 0 else (text["chars"] * 12) / wpm
        unique_texts.add(text_id)

        if wpm > best_race_wpm:
            best_race_wpm = wpm
            best_race = race
        if wpm < worst_race_wpm:
            worst_race_wpm = wpm
            worst_race = race

        break_time = race[7] - previous_race[7]
        if break_time > longest_break["time"]:
            longest_break = {
                "time": break_time,
                "start_race": {"timestamp": previous_race[7], "number": previous_race[1]},
                "end_race": {"timestamp": race[7], "number": race[1]},
            }

        previous_race = race

    average_wpm = total_wpm / race_count
    accuracy_percent = (total_accuracy / race_count) * 100
    points_per_race = points / race_count
    win_percent = (wins / race_count) * 100
    words_per_race = words / race_count
    characters_per_race = characters / race_count
    seconds_per_race = seconds / race_count
    text_count = len(unique_texts)

    summary_string = (
        f"**Average Speed:** {average_wpm:,.2f} WPM "
        f"([{worst_race['wpm']:,.2f}]({urls.replay(username, worst_race['number'], universe)}) - "
        f"[{best_race['wpm']:,.2f}]({urls.replay(username, best_race['number'], universe)}))\n"
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
        f"**Race Time:** {strings.format_duration_short(seconds)} ({seconds_per_race:,.2f}s/race)\n"
        f"**Time Difference:** {strings.format_duration_short(seconds_elapsed)}\n"
        f"**Unique Texts:** {text_count:,}\n\n"
    )

    other_stats = (
        f"**Race:** [#{first_race[1]:,}]({urls.replay(username, first_race[1], universe)}) - "
        f"<t:{int(first_race[7])}>"
    )

    if len(race_list) > 1:
        other_stats = (
            f"**First Race:** [#{first_race[1]:,}]({urls.replay(username, first_race[1], universe)}) - "
            f"<t:{int(first_race[7])}>\n"
            f"**Last Race:** [#{last_race[1]:,}]({urls.replay(username, last_race[1], universe)}) - "
            f"<t:{int(last_race[7])}>\n"
            f"**Longest Break:** {strings.format_duration_short(longest_break['time'])}"
            f" (Starting on Race [#{longest_break['start_race']['number']:,}]"
            f"({urls.replay(username, longest_break['start_race']['number'], universe)})\n"
            f"<t:{int(longest_break['start_race']['timestamp'])}> - "
            f"<t:{int(longest_break['end_race']['timestamp'])}>"
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
                  f"**Time:** {strings.format_duration_short(daily_seconds)}\n\n"
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
