from datetime import datetime, timezone

from discord import Embed
from discord.ext import commands

import database.users as users
from api.users import get_stats, get_joined
from database.bot_users import get_user
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
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    db_stats = users.get_user(username, universe)
    if universe == "play" and db_stats:
        stats["wpm_best"] = db_stats["wpm_best"]
        stats["points"] += db_stats["points_retroactive"]
        joined = db_stats["joined"]
    else:
        play_user = users.get_user(username, "play")
        if play_user:
            joined = play_user["joined"]
        else:
            joined = await get_joined(username)
        if not joined:
            return await ctx.send(embed=errors.invalid_username())

    if era_string:
        if not db_stats:
            return await ctx.send(embed=errors.import_required(username, universe, time_travel=True))
        stats = await users.time_travel_stats(stats, user)

    join_date = datetime.fromtimestamp(joined, tz=timezone.utc)
    now = dates.now()

    anniversary = ""
    if join_date.month == now.month and join_date.day == now.day:
        anniversary = " :birthday:"

    embed = Embed(color=user["colors"]["embed"])

    general_string = (
        f"{'**Name: **' + stats['display_name'] if stats['display_name'] else ''}\n"
        f"**Joined:** {join_date.strftime('%b. %d, %Y')}{anniversary}\n"
        f"**Membership:** {'Premium' if stats['premium'] else 'Basic'}"
    )
    if stats["disqualified"]:
        embed.color = colors.error
        general_string += "\n**Status:** Banned"

    stats_string = (
            f"**Races:** {stats['races']:,}\n"
            f"**Wins:** {stats['wins']:,}\n"
            f"**Points:** {stats['points']:,.0f}\n"
            f"**Average:** {stats['wpm_average']:,.2f} WPM\n"
            f"**Best:** {stats['wpm_best']:,.2f} WPM\n" +
            f"**Captcha Speed:** {stats['wpm_verified']:,.2f} WPM" * (not era_string)
    )

    embed.add_field(name="General", value=general_string, inline=False)
    embed.add_field(name="Stats", value=stats_string, inline=False)

    embeds.add_profile(embed, stats)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)
