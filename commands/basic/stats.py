from discord import Embed
from discord.ext import commands
from datetime import datetime, timezone
import utils
import errors
from database.bot_users import get_user
from api.users import get_stats, get_joined
import database.users as users

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
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)


def get_args(user, args, info):
    params = "username"
    result = utils.parse_command(user, params, args, info)
    if utils.is_embed(result):
        return result

    return result[0]


async def run(ctx, user, username):
    universe = user["universe"]
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

    join_date = datetime.fromtimestamp(joined, tz=timezone.utc)
    today = datetime.now(tz=timezone.utc)

    anniversary = ""
    if join_date.month == today.month and join_date.day == today.day:
        anniversary = " :birthday:"

    embed = Embed(color=user['colors']["embed"])

    general_string = (
                         f"{'**Name: **' + stats['display_name'] if stats['display_name'] else ''}\n"
                         f"**Joined:** {datetime.fromtimestamp(joined, tz=timezone.utc).strftime('%b. %d, %Y')}{anniversary}\n"
                         f"**Membership:** {'Premium' if stats['premium'] else 'Basic'}"
                     ) + "\n**Status:** Banned" * stats['disqualified']

    stats_string = (
        f"**Races:** {stats['races']:,}\n"
        f"**Wins:** {stats['wins']:,}\n"
        f"**Points:** {stats['points']:,.0f}\n"
        f"**Average:** {stats['wpm_average']:,.2f} WPM\n"
        f"**Best:** {stats['wpm_best']:,.2f} WPM\n"
        f"**Captcha Speed:** {stats['wpm_verified']:,.2f} WPM"
    )

    embed.add_field(name="General", value=general_string, inline=False)
    embed.add_field(name="Stats", value=stats_string, inline=False)

    utils.add_profile(embed, stats)
    utils.add_universe(embed, universe)

    await ctx.send(embed=embed)
