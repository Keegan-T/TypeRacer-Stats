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
        description="Allow me to present the [TypeRacer Anthem](https://www.udio.com/songs/rN78d8eaGt8vFrqfaQwrne)",
        color=0,
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Keegan(bot))
