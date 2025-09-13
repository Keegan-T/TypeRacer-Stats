from discord.ext import commands

from api.core import date_to_timestamp
from api.races import get_races
from api.users import get_stats
from commands.account.download import process_races
from commands.basic.stats import get_args
from commands.locks import skip_lock
from database.bot.users import get_user
from database.main import races, deleted_races, users, typing_logs
from utils import strings, errors
from utils.embeds import Page, Message, is_embed

command = {
    "name": "skippedraces",
    "aliases": ["sr"],
    "description": "Checks and imports any skipped races for a user",
    "parameters": "[username]",
    "usages": ["skippedraces keegant"],
    "temporal": False,
}


class SkippedRaces(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def skippedraces(self, ctx, *args):
        if skip_lock.locked():
            return await ctx.send(embed=errors.command_in_use())

        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username = result

        async with skip_lock:
            await run(ctx, user, username)


async def run(ctx, user, username):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())
    universe = user["universe"]

    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    race_list = await races.get_races(username, columns=["number", "timestamp"], universe=universe)
    if not race_list:
        return await ctx.send(embed=errors.no_races(universe))

    message = Message(
        ctx, user, Page(
            title="Checking Skipped Races",
            description=f"Scanning races for {strings.escape_formatting(username)}",
        ),
        universe=universe,
        time_travel=False,
    )

    await message.send()

    race_list.sort(key=lambda x: x["number"])

    numbers = [race["number"] for race in race_list]
    min_number = min(numbers)
    max_number = max(numbers)

    full_range = set(range(min_number, max_number + 1))
    existing_numbers = set(numbers)
    missing_numbers = sorted(full_range - existing_numbers)

    grouped_numbers = group_numbers(missing_numbers)
    found_races = []
    deleted_ids = deleted_races.get_ids()

    for group in grouped_numbers:
        first, last = group[0], group[-1]
        prev_race = next_race = None

        for race in race_list:
            if race["number"] < first:
                prev_race = race
            elif race["number"] > last:
                next_race = race
                break

        start_time = prev_race["timestamp"] - 10
        end_time = next_race["timestamp"] + 10

        recent_races = await get_races(username, start_time, end_time, last - first + 10, universe)
        for race in recent_races:
            number = race["rn"]
            if number in group and race["wpm"] != 0 and f"{universe}|{username}|{number}" not in deleted_ids:
                found_races.append(race)
        for i in range(len(found_races)):
            found_races[i]["t"] = date_to_timestamp(found_races[i]["t"])

    if not found_races:
        message = Message(
            ctx, user, Page(
                title="No Skipped Races Found",
                description="No skipped races were found",
            ),
            universe=universe,
            time_travel=False,
        )

        return await message.send()

    new_races, log_list, points_retroactive, total_time, characters = await process_races(
        found_races, universe, username, 0
    )
    races.add_races(new_races)
    typing_logs.add_logs(log_list)
    users.update_user_aggregate_stats(username, universe, points_retroactive, total_time, characters)
    users.update_text_stats(username, universe)

    skipped_groups = []
    for group in group_numbers([r["rn"] for r in found_races], proximity=1):
        first, last = min(group), max(group)
        if first == last:
            skipped_groups.append(f"{first:,}")
        else:
            skipped_groups.append(f"{first:,}-{last:,}")

    message = Message(
        ctx, user, Page(
            title=f"{len(found_races):,} Skipped Races Found",
            description="Imported these missing races:\n" + ", ".join(skipped_groups),
        ),
        universe=universe,
        time_travel=False,
    )

    await message.send()


def group_numbers(numbers, proximity=20):
    if not numbers:
        return []

    groups = [[numbers[0]]]
    for i in range(1, len(numbers)):
        if numbers[i] <= groups[-1][-1] + proximity:
            groups[-1].append(numbers[i])
        else:
            groups.append([numbers[i]])

    return groups


async def setup(bot):
    await bot.add_cog(SkippedRaces(bot))
