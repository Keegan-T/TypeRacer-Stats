import asyncio
from datetime import timezone

from discord import Embed, Color
from discord.ext import commands

from database.bot_users import get_user, update_date_range
from utils import embeds, strings, dates, colors
import random

travel_messages = [
    "Traveling through time",
    "Parting the temporal gates",
    "Initiating quantum leap sequence",
    "Winding the clock back",
    "Synchronizing with the spacetime continuum",
    "Dusting off the history books",
    "Calibrating time distortion field",
    "Navigating through the echoes of history",
    "Spinning the sands of time",
    "Tuning the cosmic time dial",
    "Decrypting the timeline",
    "Journeying through the time vortex",
    "Opening a portal to your past self",
    "Charging the flux capacitor",
    "Slicing through the fabric of time",
    "Engaging temporal shift engine",
    "Gathering quantum fragments of the past",
    "Tracing back the ripple in spacetime",
    "Unraveling the threads of your past",
    "Mapping the chronal flow",
    "Navigating wormholes of memory",
    "Venturing into yesteryear’s data",
    "Rewinding the cosmic tape",
    "Decoding the moments long gone",
    "Reconstructing past realities",
    "Activating chronal relay",
    "Reviving your old stats from the void",
]


command = {
    "name": "timetravel",
    "aliases": ["tt"],
    "description": "ꝐȺꞦȾ ȾĦɆ ȾɆᛗꝐꝊꞦȺŁ ₲ȺȾɆꞨ",
    "parameters": "[date_1] <date_2>",
    "usages": [
        "timetravel 2020-01-01",
        "timetravel 4/20/22 4/20/23"
    ],
}


class TimeTravel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def timetravel(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return await run(ctx, user, None, dates.now())

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        start_date, end_date = result
        await run(ctx, user, start_date, end_date)


def get_args(user, args, info):
    params = "[date]"
    if len(args) > 1:
        params += " date"

    result = strings.parse_command(user, params, args, info)
    if embeds.is_embed(result):
        return result

    start_date = None
    end_date = result[0].replace(tzinfo=timezone.utc)
    if len(result) > 1:
        start_date = result[1].replace(tzinfo=timezone.utc)
        if start_date > end_date:
            start_date, end_date = end_date, start_date

    return start_date, end_date


async def run(ctx, user, start_date, end_date):
    now = dates.now()
    if end_date > now:
        return await ctx.send(embed=future_error())

    if dates.floor_day(now) == dates.floor_day(end_date):
        end_date = None

    update_date_range(ctx.author.id, start_date, end_date)

    if start_date is None and end_date is None:
        update_date_range(ctx.author.id, start_date, end_date)
        return await ctx.send(embed=back_to_the_present(user))

    era_string = strings.get_time_travel_date_range_string(start_date, end_date)

    await ctx.send(embed=Embed(
        title=random.choice(travel_messages) + "...",
        color=Color(random.randint(0, 0xFFFFFF))
    ))
    await asyncio.sleep(0.5)

    embed = Embed(
        title="Welcome to the Past!",
        description=f"Current Era:\n{era_string}",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TimeTravel(bot))

def back_to_the_present(user):
    return Embed(
        title="Time Travel Complete",
        description="Welcome back to the present timeline.",
        color=user["colors"]["embed"],
    )

def future_error():
    return Embed(
        title="Temporal Displacement Error",
        description="Unable to establish a viable trajectory into the future.",
        color=colors.error,
    )