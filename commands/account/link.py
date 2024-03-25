from discord import Embed
from discord.ext import commands
import errors
from database.bot_users import get_user, update_username
from api.users import get_stats

info = {
    "name": "link",
    "aliases": ["register", "l"],
    "description": "Links your Discord account to a given TypeRacer username\n"
                   "Once linked, you no longer need to type your username after commands",
    "parameters": "[typeracer_username]",
    "usages": ["link keegant"],
    "import": False,
}


class Link(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def link(self, ctx, *params):
        user = get_user(ctx)
        if not params:
            return await ctx.send(embed=errors.missing_param(info))

        username = params[0].lower()
        if not get_stats(username):
            return await ctx.send(embed=errors.invalid_username())

        await run(ctx, user, username)


async def run(ctx, user, username):
    update_username(ctx.author.id, username)

    embed = Embed(
        title="Account Linked",
        description=f"<@{ctx.author.id}> has been linked to [{username}]"
                    f"(https://data.typeracer.com/pit/profile?user={username})",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Link(bot))
