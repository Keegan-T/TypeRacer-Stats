from discord.ext import commands
from src import errors
from database.bot_users import get_user
from commands.basic.stats import get_params
from api.users import get_stats

info = {
    "name": "profilepicture",
    "aliases": ["pfp"],
    "description": "Displays a user's profile picture",
    "parameters": "[username]",
    "usages": ["profilepicture keegant"],
    "import": False,
}

class ProfilePicture(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def profilepicture(self, ctx, *params):
        user = get_user(ctx)

        try:
            username = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username)

async def run(ctx, user, username):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    await ctx.send(content=f"https://data.typeracer.com/misc/pic?uid=tr:{username}")

async def setup(bot):
    await bot.add_cog(ProfilePicture(bot))