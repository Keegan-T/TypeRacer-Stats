from discord import Embed
from discord.ext import commands

from api.users import get_stats
from commands.basic.stats import get_args
from database.bot.users import get_user
from utils import errors, embeds, urls, colors

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

    if not stats["has_pic"]:
        return await ctx.send(embed=no_profile_picture())

    await ctx.send(content=f"{urls.profile_picture(username)}&refresh=1")


async def setup(bot):
    await bot.add_cog(ProfilePicture(bot))


def no_profile_picture():
    return Embed(
        title="No Profile Picture",
        description="User does not have a profile picture",
        color=colors.error,
    )
