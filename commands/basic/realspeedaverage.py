from discord import Embed
from discord.ext import commands
import colors
import errors
import utils
import urls
from config import prefix
from database.bot_users import get_user
from api.users import get_stats
from api.races import get_race_info
from commands.basic.realspeed import run as run_realspeed
from commands.locks import average_lock

info = {
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
    "import": False,
    "multiverse": True,
}


class RealSpeedAverage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def realspeedaverage(self, ctx, *params):
        if average_lock.locked():
            self.realspeedaverage.reset_cooldown(ctx)
            return await ctx.send(embed=command_in_use())

        async with average_lock:
            user = get_user(ctx)

            try:
                username, start_number, end_number, universe = await get_params(ctx, user, params)
            except ValueError:
                self.realspeedaverage.reset_cooldown(ctx)
                return

            await run(ctx, user, username, start_number, end_number, universe)


async def get_params(ctx, user, params, command=info):
    start_number = None
    end_number = None
    universe = user["universe"]

    if not params or params[0].lower() == "me":
        username = user["username"]
        if not username:
            await ctx.send(embed=errors.missing_param(command))
            raise ValueError
    else:
        username = params[0]

    if len(params) > 1:
        try:
            start_number = int(params[1])
        except ValueError:
            await ctx.send(embed=errors.invalid_param(command))
            raise

    if len(params) > 2:
        try:
            end_number = int(params[2])
        except ValueError:
            await ctx.send(embed=errors.invalid_param(command))
            raise ValueError

        if start_number > end_number:
            start_number, end_number = end_number, start_number

    return username.lower(), start_number, end_number, universe


async def run(ctx, user, username, start_number, end_number, universe, raw=False):
    if start_number == 0 or end_number == 0:
        utils.reset_cooldown(ctx.command, ctx)
        return await ctx.send(embed=errors.greater_than(0))

    stats = get_stats(username, universe=universe)
    if not stats:
        utils.reset_cooldown(ctx.command, ctx)
        return await ctx.send(embed=errors.invalid_username())

    race_count = stats["races"]
    if not end_number:
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
    reverse_lag = False
    races = "**Races**\n"

    missed_races = []
    rate_limit = False

    for i in range(start_number, end_number + 1, 1):
        race = await get_race_info(username, i, universe=universe, get_lagged=True, get_raw=raw)
        if isinstance(race, int):
            if race == 429:
                for j in range(i, end_number + 1):
                    missed_races.append(j)
                rate_limit = True
                break
            else:
                missed_races.append(i)
        elif not race or "unlagged" not in race:
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

        flag = ""
        if race["lagged"] > round(race["unlagged"], 2):
            reverse_lag = True
            flag = " :triangular_flag_on_post:"

        races += (
            f"[#{i:,}]({urls.replay(username, i, universe)}){flag}\n"
            f"**Lagged:** {race['lagged']:,.2f} WPM ({race['lag']:,.2f} WPM lag)\n"
            f"**Unlagged:** {race['unlagged']:,.2f} WPM ({race['ping']:,}ms ping)\n"
            f"**Adjusted:** {race['adjusted']:,.3f} WPM ({race['start']:,}ms start)\n"
            f"**Race Time:** {utils.format_duration_short(race['ms'] / 1000, False)}\n\n"
        )

    if lagged == 0:
        if rate_limit:
            return await ctx.send(embed=rate_limit_execeded())
        else:
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
        correction_percent = (correction / ms) * 100
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

    if missed_races:
        cause = "Rate Limit Exceeded" if rate_limit else "Missing information"

        embed.set_footer(text=(
            f"Missing Races: {', '.join([f'{r:,}' for r in missed_races])}\n"
            f"Cause: {cause}"
        ))

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
