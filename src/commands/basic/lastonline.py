from datetime import datetime

from discord import Embed
from discord.ext import commands

from api.users import get_latest_race
from api.users import get_stats
from commands.basic.stats import get_args
from database.bot_users import get_user
from utils import errors, embeds
from utils import strings

command = {
    "name": "lastonline",
    "aliases": ["lo"],
    "description": "Displays the time since a user's last race",
    "parameters": "[username]",
    "usages": ["lastonline keegant"],
}


class LastOnline(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def lastonline(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)


async def run(ctx, user, username=None):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    universe = user["universe"]

    embed = Embed(color=user["colors"]["embed"])
    embeds.add_profile(embed, stats)
    embeds.add_universe(embed, universe)

    latest_race = get_latest_race(username, universe)
    if not latest_race:
        embed.description = "User has never played"

    else:
        last_online = latest_race["t"]
        duration = datetime.now().timestamp() - last_online

        embed.add_field(
            name="Last Online",
            value=f"{strings.format_duration_short(duration)} ago\n<t:{int(last_online)}:f>"
        )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LastOnline(bot))
