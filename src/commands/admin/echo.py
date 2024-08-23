from discord.ext import commands

from commands.checks import echo_check

command = {
    "name": "echo",
    "aliases": ["e"],
    "description": "Echo",
}


class Echo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(echo_check)
    async def echo(self, ctx, *args):
        if not args:
            return

        await ctx.message.delete()
        await ctx.send(content=" ".join(args))


async def setup(bot):
    await bot.add_cog(Echo(bot))
