from discord import Embed
from discord.ext import commands

from commands.checks import admin_check
from config import bot_owner
from database.bot.banned import get_banned, ban, unban
from database.bot.users import get_user
from utils import errors, colors, strings

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

        user_id = strings.get_discord_id(args[0])
        if not user_id:
            return await ctx.send(embed=Embed(title="Invalid User", color=colors.error))

        await run(ctx, user, str(user_id))


async def run(ctx, user, user_id):
    banned = get_banned()
    author_id = str(ctx.author.id)

    embed = Embed(color=user["colors"]["embed"])

    if user_id == author_id:
        embed.title = "I Wouldn't Recommend That..."
        embed.description = f"Why would you willingly take away the\njoy of using the bot from yourself?"

    elif user_id == str(bot_owner):
        ban(author_id)
        embed.title = "You Dare Even Try?"
        embed.description = f"<@{author_id}> has just voided their bot privileges\nfor attempting to ban the owner"

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
