import asyncio

from discord import Embed
from discord.ext import commands

from commands.checks import owner_check
from database.bot.users import get_user
from database.main.races import delete_race
from utils import colors
from utils.embeds import add_universe

command = {
    "name": "deleterace",
    "aliases": ["dr"],
    "description": "Delete's a race from the database",
    "parameters": "[username] [race_number]",
    "usages": ["delete keegant 416689"],
}


class DeleteRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def deleterace(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return
        username = args[0]
        race_number = args[1]
        universe = user["universe"]

        embed = Embed(
            title="Are You Sure?",
            description=f"You are about to permanently delete race `{username}|{race_number}`\n"
                        f'Please type "confirm" to proceed with deletion',
            color=colors.warning,
        )
        add_universe(embed, universe)
        await ctx.send(embed=embed)

        def check(message):
            return message.author == ctx.author and message.content.lower() == "confirm"

        try:
            await self.bot.wait_for("message", timeout=10, check=check)
        except asyncio.TimeoutError:
            return
        else:
            await run(ctx, user, username, race_number, universe)


async def setup(bot):
    await bot.add_cog(DeleteRace(bot))


async def run(ctx, user, username, race_number, universe):
    await delete_race(username, race_number, universe)

    embed = Embed(
        title=f"Race Deleted",
        description=f"Race `{username}|{race_number}` has been removed from the database",
        color=user["colors"]["embed"],
    )
    add_universe(embed, universe)

    await ctx.send(embed=embed)
