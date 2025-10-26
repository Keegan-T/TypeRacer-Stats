from discord import Embed
from discord.ext import commands

from api.races import get_universe_multiplier
from api.users import get_stats
from commands.account.download import run as download
from commands.races.realspeed import run as run_realspeed
from config import prefix
from database.bot.users import get_user
from database.main import users, races
from utils import errors, colors, strings, embeds
from utils.embeds import Page, Message
from utils.strings import real_speed_fields

command = {
    "name": "realspeedaverage",
    "aliases": ["rsa"],
    "description": "Displays unlagged and adjusted speeds over a race interval\n"
                   "Capped at 1000 races\n"
                   f"`{prefix}realspeedaverage [username] <n>` returns the average for the last n races",
    "parameters": "[username] <first_race> <last_race>",
    "usages": [
        "realspeedaverage keegant 5",
        "realspeedaverage keegant 1 1000"
    ],
}


class RealSpeedAverage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def realspeedaverage(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, start_number, end_number = result
        universe = user["universe"]
        await run(ctx, user, username, start_number, end_number, universe)


def get_args(user, args, info):
    # Shorthand: -rsa 5
    if len(args) == 1 and user["username"]:
        username = user["username"]
        try:
            n = strings.parse_value_string(args[0])
            return username, n, None
        except ValueError:
            pass

    params = "username int:10 int"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, start_number, end_number, universe, raw=False):
    if start_number == 0 or end_number == 0:
        return await ctx.send(embed=errors.greater_than(0))

    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    profile = await get_stats(username, universe=universe)
    await download(racer=profile, universe=universe)

    total_races = profile["races"]
    if end_number is None:
        end_number = total_races
        if start_number:
            start_number = total_races - start_number + 1
        else:
            start_number = total_races - 9

    if end_number - start_number + 1 == 1:
        return await run_realspeed(ctx, user, username, start_number, False, universe, raw=raw)

    race_list = await races.get_races(
        username, columns=["*"], start_number=start_number, end_number=end_number, universe=universe,
    )

    stats = dict(
        unlagged=0,
        adjusted=0,
        start=0,
        ping=0,
        duration=0,
        accuracy=0,
        raw_unlagged=0,
        raw_adjusted=0,
        correction_time=0,
        correction_percent=0,
        pauseless_adjusted=0,
        pause_percent=0,
        pause_time=0,
    )

    race_display = "**Races**\n"
    multiplier = get_universe_multiplier(universe)

    for i, race in enumerate(race_list):
        race = dict(race)
        number = race["number"]
        chars = race["characters"]
        stats["unlagged"] += race["wpm_unlagged"]
        stats["adjusted"] += race["wpm_adjusted"]
        stats["ping"] += (multiplier * chars) / race["wpm"] - race["total_time"]
        stats["start"] += race.get("start_time") or 0
        stats["duration"] += race.get("total_time") or 0
        stats["accuracy"] += race.get("accuracy") or 0

        if not race.get("start_time") or 0:
            continue

        raw_unlagged = (multiplier * chars) / (race["start_time"] + (multiplier * (chars - 1) / race["wpm_raw"]))
        stats["raw_unlagged"] += raw_unlagged
        stats["raw_adjusted"] += race["wpm_raw"]
        stats["pauseless_adjusted"] += race["wpm_pauseless"]
        stats["correction_time"] += race["correction_time"]
        stats["correction_percent"] += race["correction_time"] / race["total_time"]
        stats["pause_time"] += race["pause_time"]
        stats["pause_percent"] += race["pause_time"] / race["total_time"]

        if raw:
            race_display = f"#{number:,} - {raw_unlagged:,.2f} / {race['wpm_raw']:,.2f}\n"
        else:
            race_display = f"#{number:,} - {race['wpm_unlagged']:,.2f} / {race['wpm_adjusted']:,.2f}\n"

    race_count = len(race_list)

    stats["unlagged"] /= race_count
    stats["adjusted"] /= race_count
    stats["ping"] /= race_count
    stats["start"] /= race_count
    stats["duration"] /= race_count
    stats["accuracy"] /= race_count

    stats["raw_unlagged"] /= race_count
    stats["raw_adjusted"] /= race_count
    stats["pauseless_adjusted"] /= race_count
    stats["correction_time"] /= race_count
    stats["correction_percent"] /= race_count
    stats["pause_time"] /= race_count
    stats["pause_percent"] /= race_count

    if ctx.invoked_with in ["rsa", "rawsa"] or race_count <= 20:
        race_display = ""

    page = Page(
        title=f"{'Raw' if raw else 'Real'} Speed Average\nRaces {start_number:,} - {end_number:,}",
        description=race_display,
        fields=real_speed_fields(stats, raw)
    )

    message = Message(
        ctx, user, page,
        profile=profile,
        universe=universe,
    )

    await message.send()


def missing_information():
    return Embed(
        title="Missing Race Information",
        description="All races in this range have missing information",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(RealSpeedAverage(bot))
