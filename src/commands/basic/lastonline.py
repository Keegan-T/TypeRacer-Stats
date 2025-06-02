from datetime import datetime

from discord.ext import commands

from api.users import get_latest_race
from api.users import get_stats
from commands.basic.stats import get_args
from database.bot.users import get_user
from utils import errors, strings
from utils.embeds import Page, Field, Message, is_embed

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
        if is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)


async def run(ctx, user, username=None):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    universe = user["universe"]
    page = Page()

    latest_race = get_latest_race(username, universe)
    if not latest_race:
        page.description = "User has never played"

    else:
        last_online = latest_race["t"]
        duration = datetime.now().timestamp() - last_online
        page.fields = [
            Field(
                name="Last Online",
                value=(
                    f"{strings.format_duration_short(duration)} ago"
                    f"\n{strings.discord_timestamp(last_online)}"
                )
            )
        ]

    message = Message(
        ctx, user, page,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(LastOnline(bot))
