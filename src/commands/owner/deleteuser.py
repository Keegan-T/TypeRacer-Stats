import asyncio

from discord import Embed
from discord.ext import commands

from commands.checks import owner_check
from database.bot.users import get_user
from database.main.users import delete_user
from utils import colors
from utils.embeds import add_universe

command = {
    "name": "deleteuser",
    "aliases": ["du"],
    "description": "Deletes a user from the database",
    "parameters": "[username]",
    "usages": ["delete keegant"],
}


class DeleteUser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def deleteuser(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return
        username = args[0]
        universe = user["universe"]

        embed = Embed(
            title="Are You Sure?",
            description=f"You are about to permanently delete user `{username}`\n"
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
            await run(ctx, user, username, universe)


async def setup(bot):
    await bot.add_cog(DeleteUser(bot))


async def run(ctx, user, username, universe):
    await delete_user(username, universe)

    embed = Embed(
        title=f"User Deleted",
        description=f"User `{username}` has been removed from the database",
        color=user["colors"]["embed"],
    )
    add_universe(embed, universe)

    await ctx.send(embed=embed)
