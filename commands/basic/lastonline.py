from discord import Embed
from discord.ext import commands
import errors
import utils
from commands.basic.stats import get_params
from api.users import get_latest_race
from database.bot_users import get_user
from utils import format_duration_short
from datetime import datetime
from api.users import get_stats

info = {
    "name": "lastonline",
    "aliases": ["lo"],
    "description": "Displays the time since a user's last race",
    "parameters": "[username]",
    "usages": ["lastonline keegant"],
    "import": False,
    "multiverse": True,
}


class LastOnline(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def lastonline(self, ctx, *params):
        user = get_user(ctx)

        try:
            username = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username)


async def run(ctx, user, username=None):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    universe = user["universe"]

    embed = Embed(color=user["colors"]["embed"])
    utils.add_profile(embed, stats)
    utils.add_universe(embed, universe)

    latest_race = get_latest_race(username, universe)
    if not latest_race:
        embed.description="User has never played"

    else:
        last_online = latest_race["t"]
        duration = datetime.now().timestamp() - last_online

        embed.add_field(name="Last Online", value=f"{format_duration_short(duration)} ago\n<t:{int(last_online)}:f>")

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LastOnline(bot))
