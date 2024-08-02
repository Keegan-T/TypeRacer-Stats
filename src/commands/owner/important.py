from discord import Embed
from discord.ext import commands

import database.important_users as important_users
from api.users import get_stats
from commands.checks import owner_check
from database.bot_users import get_user
from utils import errors

command = {
    "name": "important",
    "aliases": ["addimportant", "ai", "removeimportant", "ri"],
    "description": "Adds or removes a username from the list of users to import daily",
}


class Important(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def important(self, ctx, *args):
        user = get_user(ctx)

        username = args[0]

        stats = get_stats(username)
        if not stats:
            return await ctx.send(embed=errors.invalid_username())

        await run(ctx, user, username)


async def run(ctx, user, username):
    if ctx.invoked_with in ["addimportant", "ai"]:
        important_users.add_user(username)
        embed = Embed(
            title="User Added",
            description=f"Added {username} to daily imports",
            color=user["colors"]["embed"],
        )

    else:
        important_users.remove_user(username)
        embed = Embed(
            title="User Removed",
            description=f"Removed {username} from daily imports",
            color=user["colors"]["embed"],
        )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Important(bot))
