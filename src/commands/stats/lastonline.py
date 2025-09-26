from datetime import datetime

from discord.ext import commands

from api.users import get_stats
from commands.account.download import run as download
from commands.stats.stats import get_args
from database.bot.users import get_user
from database.main import races, users
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
    universe = user["universe"]
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    page = Page()
    if stats["races"] > 0:
        db_stats = users.get_user(username, universe)
        if not db_stats:
            return await ctx.send(embed=errors.import_required(username, universe))

        await download(racer=stats, universe=universe)
        last_online = (await races.get_races(
            username, columns=["timestamp"], order_by="timestamp", universe=universe,
            reverse=True, limit=1, text_pool=user["settings"]["text_pool"],
        ))[0][0]
        if not last_online:
            return await ctx.send(embed=errors.import_required(username, universe))

        duration = datetime.now().timestamp() - last_online
        page.fields = [
            Field(
                name="Last Online",
                value=(
                    f"{strings.format_duration(duration)} ago"
                    f"\n{strings.discord_timestamp(last_online, 'f')}"
                )
            )
        ]
    else:
        page.description = "User has never played"

    message = Message(
        ctx, user, page,
        profile=stats,
        universe=universe,
        text_pool=user["settings"]["text_pool"],
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(LastOnline(bot))
