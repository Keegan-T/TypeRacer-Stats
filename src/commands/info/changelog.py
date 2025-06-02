from discord import Embed
from discord.ext import commands

from utils import files

command = {
    "name": "changelog",
    "aliases": ["updates", "changes", "cl"],
    "description": "Displays the most recent changes for the bot",
}


class Changelog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def changelog(self, ctx):
        change_list = "".join(files.read_file("../changelog.txt")).split("\n\n")
        description = "\n\n".join([change for change in change_list[:5]])

        embed = Embed(
            title="TypeRacer Stats - Changelog",
            description=description,
            color=0,
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Changelog(bot))
