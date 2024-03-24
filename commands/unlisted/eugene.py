from discord import Embed
from discord.ext import commands

info = {
    "name": "eugene",
    "aliases": ["e5"],
    "description": "To remind us of the legend",
}


class Eugene(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def eugene(self, ctx, *params):
        await run(ctx)


async def run(ctx):
    embed = Embed(
        description="Thank you for your service :saluting_face:",
        color=7294519,
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Eugene(bot))
