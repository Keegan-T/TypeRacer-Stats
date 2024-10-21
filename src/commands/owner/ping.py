from discord import Embed
from discord.ext import commands

from commands.checks import owner_check

command = {
    "name": "ping",
    "aliases": ["p"],
    "description": "Displays the ping of the bot",
    "parameters": "",
    "usages": ["ping"],
}


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def ping(self, ctx):
        await ctx.send(embed=Embed(
            description=f"Pong! :ping_pong: {round(self.bot.latency * 1000)}ms",
            color=0,
        ))


async def setup(bot):
    await bot.add_cog(Ping(bot))
