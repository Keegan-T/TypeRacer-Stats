from discord import Embed
from discord.ext import commands

import database.races_300 as races_300
from commands.checks import admin_check
from database.bot_users import get_user
from records import update_section
from utils import strings

command = {
    "name": "clubremove",
    "aliases": ["cd"],
    "description": "Remove a user from the 300 WPM club",
    "parameters": "[username]",
    "usages": ["clubremove taran127"],
}


class ClubRemove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(admin_check)
    async def clubremove(self, ctx, *args):
        user = get_user(ctx)

        if args:
            username = args[0]

            await ctx.send(embed=Embed(
                title="Removing User",
                description=f"Removing {strings.escape_formatting(username)} from the 300 WPM club",
                color=user["colors"]["embed"],
            ))

            races_300.delete_user_scores(username)

        await update_section(self.bot, "club")

        await ctx.send(embed=Embed(
            title="Club Updated",
            description=f"Records channel has been updated",
            color=user["colors"]["embed"],
        ))


async def setup(bot):
    await bot.add_cog(ClubRemove(bot))
