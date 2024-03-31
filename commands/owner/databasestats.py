from discord import Embed
from discord.ext import commands
from database.bot_users import get_user
import database.users as users
from commands.checks import owner_check

info = {
    "name": "databasestats",
    "aliases": ["dbs", "db"],
    "description": "Displays database stats",
}


class DatabaseStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    @commands.check(owner_check)
    async def databasestats(self, ctx, *params):
        user = get_user(ctx)

        await run(ctx, user)


async def run(ctx, user):
    stats = users.get_stats()

    embed = Embed(
        title="Database Stats",
        description=(
            f"Users: {stats[0]:,}\n"
            f"Races: {stats[1]:,}"
        ),
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DatabaseStats(bot))
