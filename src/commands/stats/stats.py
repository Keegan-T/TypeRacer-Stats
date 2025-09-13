from datetime import datetime, timezone

from discord import Embed
from discord.ext import commands

import database.main.users as users
from api.users import get_racer
from database.bot.users import get_user
from utils import errors, embeds, strings, dates, colors

command = {
    "name": "stats",
    "aliases": ["profile", "s"],
    "description": "Displays stats about a user's TypeRacer account",
    "parameters": "[username]",
    "usages": ["stats keegant"],
}


async def setup(bot):
    await bot.add_cog(Stats(bot))


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def stats(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)


def get_args(user, args, info):
    params = "username"
    result = strings.parse_command(user, params, args, info)
    if embeds.is_embed(result):
        return result

    return result[0]


async def run(ctx, user, username):
    universe = user["universe"]
    era_string = strings.get_era_string(user)
    stats = await get_racer(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    db_stats = users.get_user(username, universe)
    if db_stats:
        stats["points"] += db_stats["points_retroactive"]
    if era_string:
        if not db_stats:
            return await ctx.send(embed=errors.import_required(username, universe, time_travel=True))
        stats = await users.time_travel_stats(stats, user)

    join_date = datetime.fromtimestamp(stats["joined_at"], tz=timezone.utc)
    now = dates.now()

    anniversary = ""
    if join_date.month == now.month and join_date.day == now.day:
        anniversary = " :birthday:"

    embed = Embed(color=user["colors"]["embed"])

    general_string = (
        f"{'**Name: **' + stats['name'] if stats['name'] else ''}\n"
        f"**Joined:** {join_date.strftime('%b. %d, %Y')}{anniversary}\n"
        f"**Membership:** {'Premium' if stats['premium'] else 'Basic'}"
    )

    if stats.get("keyboard", None):
        general_string += f"\n**Layout:** {stats['keyboard']}"
    if stats["dqd"]:
        embed.color = colors.error
        general_string += "\n**Status:** Banned"

    stats_string = (
            f"**Races:** {stats['total_races']:,}\n"
            f"**Wins:** {stats['total_wins']:,}\n"
            f"**Points:** {stats['points']:,.0f}\n"
            f"**Average:** {stats['avg_wpm']:,.2f} WPM\n"
            f"**Best:** {stats['best_wpm']:,.2f} WPM\n" +
            f"**Captcha Speed:** {stats['cert_wpm']:,.2f} WPM" * (not era_string)
    )

    embed.add_field(name="General", value=general_string, inline=False)
    embed.add_field(name="Stats", value=stats_string, inline=False)

    embeds.add_profile(embed, stats)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)
