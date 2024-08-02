from discord import Embed
from discord.ext import commands

from commands.checks import admin_check
from database.banned import get_banned, ban, unban
from database.bot_users import get_user
from utils import errors, colors

command = {
    "name": "ban",
    "aliases": ["perish", "unban"],
    "description": "Bans or unbans a user from being able to use the bot",
    "parameters": "[discord_id]",
    "usages": ["ban 225472450794618881"],
}


class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(admin_check)
    async def ban(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return await ctx.send(embed=errors.missing_argument(command))

        user_id = args[0].translate(args[0].maketrans("", "", "<@>"))

        try:
            await self.bot.fetch_user(user_id)
        except:
            return await ctx.send(embed=Embed(title="Unknown User", color=colors.error))

        await run(ctx, user, user_id)


async def run(ctx, user, user_id):
    banned = get_banned()

    embed = Embed(color=user["colors"]["embed"])

    if user_id == "155481579005804544":
        ban(str(ctx.author.id))
        embed = Embed(color=user["colors"]["embed"])
        embed.title = "You Dare Even Try?"
        embed.description = f"<@{ctx.author.id}> has just voided their bot privileges\nfor attempting to ban the owner"

    elif user_id in banned:
        unban(user_id)
        embed.title = "Welcome Back"
        embed.description = f"<@{user_id}> tread lightly, you're on thin ice..."

    else:
        ban(user_id)
        embed.title = "Begone!"
        embed.description = f"<@{user_id}> has been promptly vanquished!"

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Ban(bot))
