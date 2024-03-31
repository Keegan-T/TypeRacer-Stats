from discord import Embed
from discord.ext import commands
import asyncio
import colors
from database.bot_users import get_user
from database.races import delete_race
from commands.checks import owner_check

info = {
    "name": "deleterace",
    "aliases": ["dr"],
    "description": "Delete's a race from the database",
    "parameters": "[username] [race_number]",
    "usages": ["delete keegant 416689"],
    "import": False,
}


class DeleteRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    @commands.check(owner_check)
    async def deleterace(self, ctx, *params):
        user = get_user(ctx)

        if not params:
            return
        username = params[0]
        race_number = params[1]

        embed = Embed(
            title="Are You Sure?",
            description=f"You are about to permanently delete race `{username}|{race_number}`\n"
                        f'Please type "confirm" to proceed with deletion',
            color=colors.warning,
        )
        await ctx.send(embed=embed)

        def check(message):
            return message.author == ctx.author and message.content.lower() == "confirm"

        try:
            await self.bot.wait_for("message", timeout=10, check=check)
        except asyncio.TimeoutError:
            return
        else:
            await run(ctx, user, username, race_number)


async def setup(bot):
    await bot.add_cog(DeleteRace(bot))


async def run(ctx, user, username, race_number):
    delete_race(username, race_number)

    embed = Embed(
        title=f"Race Deleted",
        description=f"Race `{username}|{race_number}` has been removed from the database",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)
