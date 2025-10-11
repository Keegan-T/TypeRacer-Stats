from discord import Embed
from discord.ext import commands

import database.main.races as races
import database.main.users as users
from commands.races.fastestcompletion import get_start_time
from commands.races.races import get_stats_fields
from commands.locks import LargeQueryLock
from database.bot.users import get_user
from database.main import texts
from utils import errors, colors, strings
from utils.embeds import Page, Message, is_embed
from utils.stats import get_top_disjoint_windows

categories = ["races", "points"]
command = {
    "name": "marathon",
    "aliases": ["42"],
    "description": "Displays the maximum amount of races/points a user completed in a timeframe\n"
                   "Time can be given as seconds, or a duration string (1d 12h 30m 15s)",
    "parameters": "[username] <category> <time>",
    "defaults": {
        "category": "races",
        "time": "24 hours",
    },
    "usages": [
        "marathon keegant",
        "marathon keegant races",
        "marathon keegant points 1h30m",
    ],
}


class Marathon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def marathon(self, ctx, *args):
        user = get_user(ctx)
        args, user = strings.set_wpm_metric(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, category, seconds = result
        await run(ctx, user, username, category, seconds)


def get_args(user, args, info):
    params = f"username category:{'|'.join(categories)} duration:86400"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, category, seconds):
    if seconds <= 0:
        return await ctx.send(embed=invalid_time())

    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)
    text_pool = user["settings"]["text_pool"]
    wpm_metric = user["settings"]["wpm"]

    async with LargeQueryLock(stats["races"] > 100_000):
        text_list = texts.get_texts(universe=universe)
        text_lengths = {text["text_id"]: len(text["quote"]) for text in text_list}

        columns = [
            "text_id", "number", wpm_metric, "accuracy", "points", "characters", "rank", "racers",
            "timestamp", "wpm_raw AS wpm_raw", "start_time", "total_time", "correction_time", "pause_time",
        ]
        race_list = await races.get_races(
            username, columns=columns, universe=universe,
            start_date=user["start_date"], end_date=user["end_date"],
            text_pool=text_pool,
        )
        if not race_list:
            return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

        race_list.sort(key=lambda x: x["timestamp"])

        windows = []
        if category == "races":
            start_index = 0
            end_index = 0
            race_count = len(race_list)
            while start_index < race_count:
                start_race = race_list[start_index]
                start_time = get_start_time(start_race, text_lengths)
                while end_index < race_count and race_list[end_index]["timestamp"] - start_time <= seconds:
                    end_index += 1
                count = end_index - start_index
                if count > 0:
                    windows.append((start_index, end_index - 1, count))
                start_index += 1

        else:
            start_index = 0
            total_points = 0
            for end_index in range(len(race_list)):
                end_time = race_list[end_index]["timestamp"]
                total_points += race_list[end_index]["points"]
                while start_index <= end_index and end_time - get_start_time(race_list[start_index], text_lengths) > seconds:
                    total_points -= race_list[start_index]["points"]
                    start_index += 1
                windows.append((start_index, end_index, total_points))

        windows.sort(key=lambda x: -x[2])
        top_windows = get_top_disjoint_windows(windows, 10)

        best = top_windows[0]
        race_range = race_list[best[0]:best[1] + 1]
        start_time = race_range[0]["timestamp"]
        end_time = race_range[-1]["timestamp"]
        fields, footer = get_stats_fields(
            username, race_range, start_time, end_time, universe,
            text_pool=text_pool,
        )

    description = ""
    for i in range(len(top_windows)):
        window = top_windows[i]
        amount = window[2]
        start_number = race_list[window[0]]["number"]
        end_number = race_list[window[1]]["number"]
        description += f"{i + 1}. {amount:,.0f} (Races {start_number:,} - {end_number:,})\n"

    period_string = strings.format_duration(seconds, False)
    category = category[:-1].title()

    pages = [
        Page(
            title=f"Best {category} Marathons ({period_string} period)",
            description=f"{top_windows[0][2]:,.0f} {category}s",
            fields=fields,
            footer=footer,
            button_name="Best",
        ),
        Page(
            f"Top 10 Best {category} Marathon ({period_string} period)",
            description, button_name="Top 10",
        )
    ]

    message = Message(
        ctx, user, pages,
        profile=stats,
        universe=universe,
        text_pool=text_pool,
        wpm_metric=wpm_metric,
    )

    await message.send()


def invalid_time():
    return Embed(
        title="Invalid Time",
        description="Time must be greater than 0 seconds",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Marathon(bot))
