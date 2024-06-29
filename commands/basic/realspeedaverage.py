import asyncio

from discord import Embed
from discord.ext import commands
import utils
import errors
import urls
import colors
from config import prefix
from database.bot_users import get_user
from api.users import get_stats
from api.races import get_race_html_bulk, get_race_details
from commands.basic.realspeed import run as run_realspeed
import commands.locks as locks

command = {
    "name": "realspeedaverage",
    "aliases": ["rsa", "realspeedaverageraces", "rsar", "rsa*"],
    "description": "Displays unlagged and adjusted speeds over a race interval\n"
                   "Capped at 10 races\n"
                   f"`{prefix}realspeedaverage [username] <n>` returns the average for the last n races\n"
                   f"`{prefix}realspeedaverageraces` will list the speeds of each individual race",
    "parameters": "[username] <first_race> <last_race>",
    "usages": [
        "realspeedaverage keegant 5",
        "realspeedaverage keegant 101 110"
    ],
    "multiverse": True,
}


class RealSpeedAverage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def realspeedaverage(self, ctx, *args):
        if locks.average_lock.locked():
            self.realspeedaverage.reset_cooldown(ctx)
            return await ctx.send(embed=command_in_use())

        async with locks.average_lock:
            user = get_user(ctx)

            result = get_args(user, args, command)
            if utils.is_embed(result):
                self.realspeedaverage.reset_cooldown(ctx)
                return await ctx.send(embed=result)

            username, start_number, end_number = result
            universe = user["universe"]
            await run(ctx, user, username, start_number, end_number, universe)


def get_args(user, args, info):
    params = "username int:10 int"

    return utils.parse_command(user, params, args, info)


async def run(ctx, user, username, start_number, end_number, universe, raw=False):
    if start_number == 0 or end_number == 0:
        utils.reset_cooldown(ctx.command, ctx)
        return await ctx.send(embed=errors.greater_than(0))

    stats = get_stats(username, universe=universe)
    if not stats:
        utils.reset_cooldown(ctx.command, ctx)
        return await ctx.send(embed=errors.invalid_username())

    race_count = stats["races"]
    if end_number is None:
        end_number = race_count
        if start_number:
            start_number = race_count - start_number + 1
        else:
            start_number = race_count - 9

    if end_number - start_number > 9:
        utils.reset_cooldown(ctx.command, ctx)
        return await ctx.send(embed=max_range())

    race_count = end_number - start_number + 1

    if race_count == 1:
        utils.reset_cooldown(ctx.command, ctx)
        return await run_realspeed(ctx, user, username, start_number, False, universe, raw=raw)

    lagged = 0
    unlagged = 0
    adjusted = 0
    lag = 0
    ping = 0
    start = 0
    ms = 0
    raw_unlagged = 0
    raw_adjusted = 0
    correction = 0
    correction_percent = 0
    reverse_lag = False
    races = "**Races**\n"

    links = []
    for i in range(start_number, end_number + 1):
        links.append(urls.replay(username, i, universe))

    race_htmls = await get_race_html_bulk(links)
    race_list = [await get_race_details(html, get_raw=raw, universe=universe) for html in race_htmls]

    missed_races = []

    for i, race in enumerate(race_list):
        race_number = start_number + i
        if not race or "unlagged" not in race:
            missed_races.append(i)
            continue

        lagged += race["lagged"]
        unlagged += race["unlagged"]
        adjusted += race["adjusted"]
        lag += race["lag"]
        ping += race["ping"]
        start += race["start"]
        ms += race["ms"]
        if raw:
            raw_unlagged += race["raw_unlagged"]
            raw_adjusted += race["raw_adjusted"]
            correction += race["correction"]
            correction_percent += race["correction"] / race["ms"]

        flag = ""
        if race["lagged"] > round(race["unlagged"], 2):
            reverse_lag = True
            flag = " :triangular_flag_on_post:"

        races += (
            f"[#{race_number:,}]({urls.replay(username, race_number, universe)}){flag}\n"
            f"**Lagged:** {race['lagged']:,.2f} WPM ({race['lag']:,.2f} WPM lag)\n"
            f"**Unlagged:** {race['unlagged']:,.2f} WPM ({race['ping']:,}ms ping)\n"
            f"**Adjusted:** {race['adjusted']:,.3f} WPM ({race['start']:,}ms start)\n"
            f"**Race Time:** {utils.format_duration_short(race['ms'] / 1000, False)}\n\n"
        )

    if lagged == 0:
        return await ctx.send(embed=missing_information())
    
    race_count -= len(missed_races)

    lagged /= race_count
    unlagged /= race_count
    adjusted /= race_count
    lag /= race_count
    ping /= race_count
    start /= race_count
    ms /= race_count

    real_speeds = (
        f"**Lagged:** {lagged:,.2f} WPM\n"
        f"**Unlagged:** {unlagged:,.2f} WPM\n"
        f"**Adjusted:** {adjusted:,.3f} WPM\n"
        f"**Race Time:** {utils.format_duration_short(ms / 1000, False)}\n\n"
    )

    if raw:
        raw_unlagged /= race_count
        raw_adjusted /= race_count
        correction /= race_count
        correction_percent /= race_count
        correction_percent *= 100
        real_speeds += (
            f"**Raw Unlagged:** {raw_unlagged:,.2f} WPM\n"
            f"**Raw Adjusted:**  {raw_adjusted:,.3f} WPM\n"
            f"**Correction Time:** {utils.format_duration_short(correction / 1000, False)} "
            f"({correction_percent:,.2f}%)\n\n"
        )

    real_speeds += (
        f"**Lag:** {lag:,.2f} WPM\n"
        f"**Ping:** {ping:,.0f}ms\n"
        f"**Start:** {start:,.0f}ms\n"
    )

    if ctx.invoked_with in ["realspeedaverageraces", "rsar", "rsa*"]:
        real_speeds = races + "**Averages**\n" + real_speeds

    if reverse_lag:
        real_speeds = ":triangular_flag_on_post: Reverse Lag Detected :triangular_flag_on_post:\n\n" + real_speeds

    embed = Embed(
        title=f"{'Raw' if raw else 'Real'} Speed Average\nRaces {start_number:,} - {end_number:,}",
        description=real_speeds,
        color=user["colors"]["embed"],
    )

    if reverse_lag:
        embed.color = colors.error

    utils.add_profile(embed, stats)
    utils.add_universe(embed, universe)

    # if missed_races:
    #     cause = "Rate Limit Exceeded" if rate_limit else "Missing information"
    #     message = (
    #         f"Missing Races: {', '.join([f'{r:,}' for r in missed_races])}\n"
    #         f"Cause: {cause}\n\n"
    #     )
    #
    #     embed.description = message + embed.description

    await ctx.send(embed=embed)


def missing_information():
    return Embed(
        title="Missing Race Information",
        description="All races in this range have missing information",
        color=colors.error,
    )


def rate_limit_execeded():
    return Embed(
        title="Rate Limit Exceeded",
        description="Reached the rate limit, please wait before trying again",
        color=colors.error,
    )


def max_range():
    return Embed(
        title="Too Many Races",
        description="Can only check the average of up to 10 races at once",
        color=colors.error,
    )


def command_in_use():
    return Embed(
        title=f"Command In Use",
        description=f"Please wait until the current usage has finished",
        color=colors.warning,
    )


async def setup(bot):
    await bot.add_cog(RealSpeedAverage(bot))
