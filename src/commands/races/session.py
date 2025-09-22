from discord.ext import commands

import database.main.races as races
import database.main.users as users
from commands.races.fastestcompletion import get_start_time
from commands.races.races import get_stats_fields
from commands.locks import LargeQueryLock
from database.bot.users import get_user
from database.main import texts
from utils import errors, strings
from utils.embeds import Page, Message, is_embed
from utils.stats import get_top_disjoint_windows

command = {
    "name": "session",
    "aliases": ["ss"],
    "description": "Displays the maximum duration/race get_competition_count sessions for a user with a given minimum break\n"
                   "A session ends whenever two races are greater apart in time than the minimum break",
    "parameters": "[username] <category> <time>",
    "defaults": {
        "category": "races",
        "time": "30 minutes",
    },
    "usages": [
        "session keegant",
        "session keegant races 1h30m",
        "session keegant time 1h30m",
    ],
}


class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def session(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, category, seconds = result
        await run(ctx, user, username, category, seconds)


def get_args(user, args, info):
    params = f"username category:races|time duration:1800"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, category, seconds):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    async with LargeQueryLock(stats["races"] > 100_000):
        text_list = texts.get_texts(universe=universe)
        text_lengths = {text["text_id"]: len(text["quote"]) for text in text_list}

        columns = [
            "text_id", "number", "wpm", "accuracy", "points", "characters", "rank", "racers",
            "timestamp", "wpm_raw", "start_time", "total_time", "correction_time", "pause_time",
        ]
        race_list = await races.get_races(
            username, columns=columns, universe=universe,
            start_date=user["start_date"], end_date=user["end_date"],
            text_pool=user["settings"]["text_pool"],
        )
        if not race_list:
            return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)
        race_list.sort(key=lambda x: x["timestamp"])

        windows = []
        start_index = 0

        if category == "races":
            current_session = 1
            for i in range(1, len(race_list)):
                start_time = get_start_time(race_list[i - 1], text_lengths)
                time_difference = race_list[i]["timestamp"] - start_time
                if time_difference < seconds:
                    current_session += 1
                else:
                    end_index = i - 1
                    windows.append((start_index, end_index, current_session))
                    start_index = i
                    current_session = 1

        else:
            current_session = 0
            for i in range(1, len(race_list)):
                start_time = get_start_time(race_list[i - 1], text_lengths)
                time_difference = race_list[i]["timestamp"] - start_time
                if time_difference < seconds:
                    current_session += time_difference
                else:
                    end_index = i - 1
                    windows.append((start_index, end_index, current_session))
                    start_index = i
                    current_session = 0

        end_index = len(race_list) - 1
        windows.append((start_index, end_index, current_session))
        windows.sort(key=lambda x: -x[2])
        top_windows = get_top_disjoint_windows(windows, 10)

        best = top_windows[0]
        race_range = race_list[best[0]:best[1] + 1]
        start_time = get_start_time(race_range[0], text_lengths)
        end_time = race_range[-1]["timestamp"]
        fields, footer = get_stats_fields(
            username, race_range, start_time, end_time, universe,
            text_pool=user["settings"]["text_pool"],
        )

    interval = f" ({strings.format_duration(seconds, False)} interval)"
    title = f"{'Longest' if category == 'time' else 'Highest Race'} Session"

    description = ""
    for i in range(len(top_windows)):
        window = top_windows[i]
        value = window[2]
        start_number = race_list[window[0]]["number"]
        end_number = race_list[window[1]]["number"]
        if category == "races":
            formatted = f"{value:,.0f}"
        else:
            formatted = strings.format_duration(value, False)
        description += f"{i + 1}. {formatted} (Races {start_number:,} - {end_number:,})\n"

    pages = [
        Page(
            title=title + interval,
            description=(
                strings.format_duration(end_time - start_time, False)
                if category == "time" else f"{top_windows[0][2]:,} Races"
            ),
            fields=fields,
            footer=footer,
            button_name="Best",
        ),
        Page(
            f"Top 10 {title}s{interval}",
            description, button_name="Top 10",
        )
    ]

    message = Message(
        ctx, user, pages,
        title=title,
        profile=stats,
        universe=universe,
        text_pool=user["settings"]["text_pool"],
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Session(bot))
