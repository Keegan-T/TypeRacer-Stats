from discord import Embed
from discord.ext import commands

info = {
    "name": "keegan",
    "aliases": ["keegant", "kegnat", "kt"],
    "description": "keegan",
}


class Keegan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def keegan(self, ctx, *params):
        await run(ctx)


async def run(ctx):
    embed = Embed(
        title="hi",
        description="sup",
        color=0,
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Keegan(bot))
