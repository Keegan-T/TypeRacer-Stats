from discord import Embed
from discord.ext import commands

import database.main.users as users
from commands.checks import owner_check
from database.bot.users import get_user

command = {
    "name": "databasestats",
    "aliases": ["dbs", "db"],
    "description": "Displays database stats",
}


class DatabaseStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def databasestats(self, ctx):
        user = get_user(ctx)

        await run(ctx, user)


async def run(ctx, user):
    race_count, text_count, user_count, universe_count = users.get_database_stats()

    embed = Embed(
        title="Database Stats",
        description=(
            f"Races: {race_count:,}\n"
            f"Texts: {text_count:,}\n"
            f"Users: {user_count:,}\n"
            f"Universes: {universe_count:,}"
        ),
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DatabaseStats(bot))
