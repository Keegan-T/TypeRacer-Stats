import asyncio

from discord import Embed
from discord.ext import commands

from commands.checks import owner_check
from database.bot_users import get_user
from database.users import delete_user
from utils import colors

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

        embed = Embed(
            title="Are You Sure?",
            description=f"You are about to permanently delete user `{username}`\n"
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
            await run(ctx, user, username)


async def setup(bot):
    await bot.add_cog(DeleteUser(bot))


async def run(ctx, user, username):
    delete_user(username)

    embed = Embed(
        title=f"User Deleted",
        description=f"User `{username}` has been removed from the database",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)
