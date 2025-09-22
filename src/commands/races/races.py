from datetime import datetime, timezone

import numpy as np
from dateutil.relativedelta import relativedelta
from discord import Embed
from discord.ext import commands

import database.main.races as races
import database.main.texts as texts
import database.main.users as users
from commands.locks import LargeQueryLock
from database.bot.users import get_user
from utils import errors, colors, urls, strings, dates
from utils.embeds import Message, Page, Field, is_embed

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
        if is_embed(result):
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
        if not is_embed(result):
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

    if is_embed(result):
        params = "username date date"
        result = strings.parse_command(user, params, args, info)

        if is_embed(result):
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

    async with LargeQueryLock(stats["races"] > 100_000):
        era_string = strings.get_era_string(user)
        if era_string:
            stats = await users.filter_stats(stats, user)

        if start_number and not end_number:
            end_number = stats["races"]

        if start_date and not end_date:
            end_date = dates.now()

        start_date, end_date = dates.time_travel_dates(user, start_date, end_date)
        user_start, user_end = user["start_date"], user["end_date"]

        title = "Race Stats - "
        columns = [
            "text_id", "number", "wpm", "accuracy", "points", "characters", "rank", "racers",
            "timestamp", "wpm_raw", "start_time", "total_time", "correction_time", "pause_time",
        ]
        if start_date is None and start_number is None:
            title += "All-Time"
            start = stats["joined"]
            end = dates.now().timestamp()
            if user_start: start = max(start, user_start)
            if user_end: end = min(end, user_end)
            race_list = await races.get_races(
                username, columns, None if start == stats["joined"] else start,
                None if end == dates.now().timestamp() else end, universe=universe,
                text_pool=user["settings"]["text_pool"],
            )

        elif start_date is None:
            end_number = min(end_number, stats["races"])
            title += f"Races {start_number:,} - {end_number:,}"
            race_list = await races.get_races(
                username, columns, start_number=start_number,
                end_number=end_number, universe=universe,
                start_date=user_start, end_date=user_end,
                text_pool=user["settings"]["text_pool"],
            )
            if race_list:
                start = race_list[0]["timestamp"]
                end = race_list[-1]["timestamp"] + 0.01

        else:
            start = start_date.timestamp()
            if start < stats["joined"]:
                start = stats["joined"]
                start_date = datetime.fromtimestamp(stats["joined"], tz=timezone.utc)
            end = end_date.timestamp()
            title += strings.get_display_date_range(start_date, end_date)
            race_list = await races.get_races(
                username, columns, start_date.timestamp(),
                end_date.timestamp(), universe=universe,
                text_pool=user["settings"]["text_pool"],
            )

        if not race_list:
            return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)
        race_list.sort(key=lambda x: x["timestamp"])

        fields, footer = get_stats_fields(
            username, race_list, start, end, universe,
            text_pool=user["settings"]["text_pool"],
        )

    page = Page(title, fields=fields, footer=footer)

    message = Message(
        ctx, user, page,
        profile=stats,
        universe=universe,
        text_pool=user["settings"]["text_pool"],
    )

    await message.send()


def get_stats_fields(username, race_list, start_time, end_time, universe="play", detailed=True, text_pool="all"):
    fields = []
    footer = None

    average_wpm = {"total": 0, "count": 0}
    average_wpm_raw = {"total": 0, "count": 0}
    average_accuracy = {"total": 0, "count": 0}
    average_start = {"total": 0, "count": 0}
    average_pause = {"total": 0, "count": 0}
    average_correction = {"total": 0, "count": 0}
    race_count = len(race_list)
    end_time = min(end_time, datetime.now(timezone.utc).timestamp())
    text_list = texts.get_texts(as_dictionary=True, universe=universe)
    wins = 0
    points = 0
    best_last_10 = 0
    current_last_10 = 0
    words = 0
    characters = 0
    total_time = 0
    text_improvements = 0
    total_wpm_gain = 0
    text_best_list = users.get_text_bests(username, until=race_list[0][8], text_pool=text_pool)
    text_bests = {text_id: wpm for text_id, wpm in text_best_list}
    disabled_text_ids = texts.get_disabled_text_ids()
    unique_texts = set()
    best_race = {}
    worst_race = {}
    best_race_wpm = 0
    worst_race_wpm = 72000000
    first_race = race_list[0]
    last_race = race_list[-1]
    race_difference = last_race["number"] - first_race["number"] + 1
    seconds_elapsed = last_race["timestamp"] - first_race["timestamp"]
    days = dates.count_unique_dates(start_time, end_time - 0.001)
    longest_break = {"time": 0, "start_number": {}}
    standard_deviation = np.std([race["wpm"] for race in race_list])

    previous_race = race_list[0]
    for i, race in enumerate(race_list):
        if race["racers"] > 1 and race["rank"] == 1:
            wins += 1

        points += race["points"]
        wpm = race["wpm"]
        average_wpm["total"] += wpm
        average_wpm["count"] += 1

        accuracy = race["accuracy"]
        if accuracy > 0:
            average_accuracy["total"] += accuracy
            average_accuracy["count"] += 1

        wpm_raw = race["wpm_raw"]
        if wpm_raw:
            average_wpm_raw["total"] += wpm_raw
            average_wpm_raw["count"] += 1
            average_correction["total"] += race["correction_time"] / race["total_time"]
            average_correction["count"] += 1
            average_pause["total"] += race["pause_time"]
            average_pause["count"] += 1
            start = race["start_time"]
            if start >= 10:
                average_start["total"] += race["start_time"]
                average_start["count"] += 1

        text_id = race["text_id"]
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
            current_last_10 -= race_list[i - 9]["wpm"]

        total_time += race["total_time"]
        unique_texts.add(text_id)

        if wpm > best_race_wpm:
            best_race_wpm = wpm
            best_race = race
        if wpm < worst_race_wpm:
            worst_race_wpm = wpm
            worst_race = race

        break_time = race["timestamp"] - previous_race["timestamp"]
        if break_time >= longest_break["time"]:
            longest_break = {
                "time": break_time,
                "start_number": previous_race["number"],
            }

        previous_race = race

        if text_id in disabled_text_ids:
            continue

        best = text_bests.get(text_id)
        if best is not None:
            if wpm > best:
                total_wpm_gain += (wpm - best)
                text_improvements += 1
                text_bests[text_id] = wpm
        else:
            text_improvements += 1
            total_wpm_gain += wpm
            text_bests[text_id] = wpm

    seconds = total_time / 1000
    average_string = (
        f"**Average Speed:** {average_wpm["total"] / average_wpm["count"]:,.2f} WPM "
        f"({average_accuracy["total"] / max(average_accuracy["count"], 1):.2%} Accuracy)\n"
    )
    raw_string = (
        f"**Raw Speed:** {average_wpm_raw["total"] / max(average_wpm_raw["count"], 1):,.2f} WPM "
        f"({average_correction["total"] / max(average_correction["count"], 1):.2%} Correction)\n"
    )
    races_string = (
        f"**Races:** {race_count:,} "
        f"([#{first_race[1]:,}]({urls.replay(username, first_race[1], universe)}) - "
        f"[#{last_race[1]:,}]({urls.replay(username, last_race[1], universe)}))\n"
    )
    wins_string = f"**Wins:** {wins:,} ({wins / race_count:.2%} win rate)\n"
    points_string = f"**Points:** {points:,.0f} ({points / race_count:,.2f} points/race)\n"

    speed_string = (
        f"{average_string}"
        f"{raw_string}"
        f"**Range:** {best_race['wpm'] - worst_race['wpm']:,.2f} WPM "
        f"([{worst_race['wpm']:,.2f}]({urls.replay(username, worst_race['number'], universe)}) - "
        f"[{best_race['wpm']:,.2f}]({urls.replay(username, best_race['number'], universe)}))\n"
        f"**Starts:** {average_start["total"] / max(average_start["count"], 1):,.0f}ms / "
        f"**Pauses:** {average_pause["total"] / max(average_pause["count"], 1):,.0f}ms / "
        f"**Std. Dev:** ± {standard_deviation:,.2f} WPM\n"
    )

    if not detailed:
        fields.append(Field(name="Summary", value=(
            f"{average_string}"
            f"{raw_string}"
            f"{races_string}"
            f"{wins_string}"
            f"{points_string}"
        ), inline=False))
        return fields, None

    if len(race_list) > 10:
        speed_string += f"**Best Last 10:** {best_last_10 / 10:,.2f} WPM\n"

    fields.append(Field(name="Speed", value=speed_string, inline=False))

    stats_string = (
        f"{races_string}"
        f"{wins_string}"
        f"{points_string}"
        f"**Words Typed:** {words:,} ({words / race_count:,.2f} words/race)\n"
        f"**Characters Typed:** {characters:,} ({characters / race_count:,.2f} chars/race)\n"
        f"**Race Time:** {strings.format_duration(seconds)} ({seconds / race_count:,.2f}s/race)\n"
        f"**Timespan:** {strings.format_duration(seconds_elapsed)} "
        f"({strings.discord_timestamp(first_race['timestamp'], 'd')} - "
        f"{strings.discord_timestamp(last_race['timestamp'], 'd')})\n"
        f"**Longest Break:** {strings.format_duration(longest_break['time'])} "
        f"(Starting on [#{longest_break['start_number']:,}]"
        f"({urls.replay(username, longest_break['start_number'], universe)}))\n"
        f"**Unique Texts:** {len(unique_texts):,}\n"
    )

    if total_wpm_gain > 0:
        stats_string += (
            f"**Text Improvements:** {text_improvements:,} (+{total_wpm_gain:,.2f} WPM)\n"
        )
    fields.append(Field(name="Stats", value=stats_string, inline=False))

    if days > 1:
        daily_races = race_count / days
        daily_points = points / days
        daily_seconds = seconds / days
        daily_string = (
            f"**Races:** {daily_races:,.2f}\n"
            f"**Points:** {daily_points:,.2f}\n"
            f"**Time:** {strings.format_duration(daily_seconds)}\n\n"
        )
        fields.append(Field(name=f"**Daily Average (Over {days:,} Days)**\n", value=daily_string, inline=False))

    if race_difference > len(race_list) and text_pool == "all":
        footer = f"Missing races found in this range, actual races completed: {race_difference:,}"

    return fields, footer


def same_dates():
    return Embed(
        title="Invalid Date Range",
        description="Dates cannot be the same",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Races(bot))
