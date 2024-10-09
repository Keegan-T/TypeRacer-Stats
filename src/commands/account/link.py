from discord import Embed
from discord.ext import commands

from api.users import get_stats
from commands.basic.download import run as download
from commands.basic.stats import get_args
from config import prefix
from database.bot_users import get_user, update_username
from utils import errors, embeds, urls

command = {
    "name": "link",
    "aliases": ["register", "l"],
    "description": "Links your Discord account to a given TypeRacer username\n"
                   "Once linked, you no longer need to type your username after commands",
    "parameters": "[typeracer_username]",
    "usages": ["link keegant"],
}


class Link(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def link(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)


async def run(ctx, user, username):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    update_username(ctx.author.id, username)
    new_user = user["username"] is None

    description = (
        f"<@{ctx.author.id}> has been linked to [{username}]"
        f"({urls.profile(username)})\n\n"
    )

    if new_user:
        description += (
            f"You no longer need to type your username after commands.\n"
            "You can also use \"me\" in the place of your username.\n"
            f"Example: `{prefix}improvement me day`"
        )

    embed = Embed(
        title="Account Linked",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)

    if new_user and stats["races"] > 0:
        await download(ctx=ctx, bot_user=user, stats=stats)


async def setup(bot):
    await bot.add_cog(Link(bot))
