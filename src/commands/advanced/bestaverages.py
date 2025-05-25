from datetime import datetime, timezone

from discord import Embed
from discord.ext import commands

import database.main.races as races
import database.main.users as users
from database.bot.users import get_user
from utils import errors, colors, strings, dates
from utils.embeds import Message, Page, is_embed

command = {
    "name": "bestaverages",
    "aliases": ["ba"],
    "description": "Displays a user's top 10 best average of n races\n"
                   "Averages will not contain overlapping races",
    "parameters": "[username] <n>",
    "defaults": {
        "n": 10,
    },
    "usages": ["bestaverages keegant 10"],
}


class BestAverages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def bestaverages(self, ctx, *args):
        user = get_user(ctx)
        args, user = dates.set_command_date_range(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, n = result
        await run(ctx, user, username, n)


def get_args(user, args, info):
    params = "username int:10"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, n):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    era_string = strings.get_era_string(user)
    if era_string:
        stats = await users.time_travel_stats(stats, user)

    if n < 1:
        return await ctx.send(embed=errors.greater_than(0))

    if n > stats["races"]:
        return await ctx.send(embed=not_enough_races(), content=era_string)

    race_list = await races.get_races(
        username, columns=["wpm", "number", "timestamp"], universe=universe,
        start_date=user["start_date"], end_date=user["end_date"]
    )
    race_list.sort(key=lambda x: x[2])

    averages = [sum([race[0] for race in race_list[:n]])]
    start_index = 0
    end_index = n
    while end_index < len(race_list):
        average = averages[start_index]
        average -= race_list[start_index][0]
        average += race_list[end_index][0]
        averages.append(average)
        start_index += 1
        end_index += 1

    pages = []
    page_count = 10
    per_page = min(10, len(averages) // 10 + 1)

    for _ in range(page_count):
        description = ""
        for _ in range(per_page):
            best = max(averages)
            if best == 0:
                break
            best_index = averages.index(best)
            for i in range(-n + 1, n):
                target_index = best_index + i
                if 0 <= target_index < len(averages):
                    averages[target_index] = 0

            start_number = race_list[best_index][1]
            end_number = race_list[best_index + n - 1][1]
            start_timestamp = race_list[best_index][2]
            end_timestamp = race_list[best_index + n - 1][2]
            date_range = strings.get_display_date_range(
                datetime.fromtimestamp(start_timestamp, tz=timezone.utc),
                datetime.fromtimestamp(end_timestamp, tz=timezone.utc),
            )
            description += (
                f"**{date_range}**\n{best / n:,.2f} WPM: "
                f"(Races {start_number:,} - {end_number:,})\n\n"
            )
        pages.append(Page(description=description))
        if sum(averages) == 0:
            break

    title = f"Best Last {n:,} Averages"

    message = Message(
        ctx=ctx,
        user=user,
        pages=pages,
        title=title,
        profile=stats,
        universe=universe,
    )

    await message.send()


def not_enough_races():
    return Embed(
        title="Not Enough Races",
        description="User has not completed this many races",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(BestAverages(bot))
