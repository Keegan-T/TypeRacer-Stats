from discord.ext import commands
from config import bot_admins, supporters

info = {
    "name": "echo",
    "aliases": ["e"],
    "description": "Echo",
}

def echo_check(ctx):
    return ctx.author.id in bot_admins + supporters

class Echo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    @commands.check(echo_check)
    async def echo(self, ctx, *params):
        if not params:
            return

        await ctx.message.delete()
        await run(ctx, " ".join(params))

async def run(ctx, message):
    await ctx.send(content=message)

async def setup(bot):
    await bot.add_cog(Echo(bot))