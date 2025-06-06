from discord.ext import commands

from api.users import get_stats
from commands.basic.stats import get_args
from database.bot.users import get_user
from utils import errors, embeds, urls

command = {
    "name": "profilepicture",
    "aliases": ["pfp"],
    "description": "Displays a user's profile picture",
    "parameters": "[username]",
    "usages": ["profilepicture keegant"],
}


class ProfilePicture(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def profilepicture(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, username)


async def run(ctx, username):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    await ctx.send(content=f"{urls.profile_picture(username)}&refresh=1")


async def setup(bot):
    await bot.add_cog(ProfilePicture(bot))
