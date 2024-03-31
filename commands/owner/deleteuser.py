from discord import Embed
from discord.ext import commands
import asyncio
import colors
from database.bot_users import get_user
from database.users import delete_user
from commands.checks import owner_check

info = {
    "name": "deleteuser",
    "aliases": ["du"],
    "description": "Delete's a user from the database",
    "parameters": "[username]",
    "usages": ["delete keegant"],
}


class DeleteUser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    @commands.check(owner_check)
    async def deleteuser(self, ctx, *params):
        user = get_user(ctx)

        if not params:
            return
        username = params[0]

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
