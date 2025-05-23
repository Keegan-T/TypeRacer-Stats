from discord import Embed
from discord.ext import commands

from api.races import get_races
from api.users import get_stats
from commands.basic.stats import get_args
from commands.locks import skip_lock
from database import races
from database.bot_users import get_user
from utils import embeds, strings, errors

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
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result

        async with skip_lock:
            await run(ctx, user, username)


async def run(ctx, user, username):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())
    universe = user["universe"]

    race_list = await races.get_races(username, columns=["number", "timestamp"], universe=universe)
    if not race_list:
        return await ctx.send(embed=errors.no_races(universe))

    embed = Embed(
        title="Checking Skipped Races",
        description=f"Scanning races for {strings.escape_formatting(username)}",
        color=user["colors"]["embed"],
    )
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)

    race_list.sort(key=lambda x: x["number"])

    numbers = [race["number"] for race in race_list]
    min_number = min(numbers)
    max_number = max(numbers)

    full_range = set(range(min_number, max_number + 1))
    existing_numbers = set(numbers)
    missing_numbers = sorted(full_range - existing_numbers)

    grouped_numbers = group_numbers(missing_numbers)
    found_races = []

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

        race_range = await get_races(username, start_time, end_time, last - first + 10, universe)
        for race in race_range:
            if race["gn"] in group and race["wpm"] != 0:
                found_races.append((
                    strings.race_id(username, race["gn"]), username, race["tid"], race["gn"],
                    race["wpm"], race["ac"], race["pts"], race["r"], race["np"], race["t"],
                ))

    if not found_races:
        embed = Embed(
            title="No Skipped Races Found",
            description="No skipped races were found",
            color=user["colors"]["embed"],
        )
        embeds.add_universe(embed, universe)

        return await ctx.send(embed=embed)

    races.add_races(found_races, universe)

    skipped_groups = []
    for group in group_numbers([r[3] for r in found_races], proximity=1):
        first, last = min(group), max(group)
        if first == last:
            skipped_groups.append(f"{first:,}")
        else:
            skipped_groups.append(f"{first:,}-{last:,}")

    embed = Embed(
        title=f"{len(found_races):,} Skipped Races Found",
        description="Imported these missing races:\n" + ", ".join(skipped_groups),
        color=user["colors"]["embed"],
    )
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


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
