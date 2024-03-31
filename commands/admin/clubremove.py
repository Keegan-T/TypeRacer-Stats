from discord import Embed
from discord.ext import commands
import errors
import utils
from database.bot_users import get_user
from commands.admin.ban import admin_check
import database.races_300 as races_300
from database import records

info = {
    "name": "clubremove",
    "aliases": ["cr"],
    "description": "Remove a user from the 300 WPM club",
    "parameters": "[username]",
    "usages": ["clubremove keegant"],
}

class ClubRemove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    @commands.check(admin_check)
    async def clubremove(self, ctx, *params):
        user = get_user(ctx)

        if not params:
            return
        username = params[0]

        await run(ctx, user, username)
        await records.update_300_club(self.bot)

async def run(ctx, user, username):
    races_300.delete_user_scores(username)

    embed = Embed(
        title="User Removed",
        description=f"Removed all {utils.escape_discord_format(username)} scores from the 300 WPM Club",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ClubRemove(bot))