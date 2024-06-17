from discord import Embed
from discord.ext import commands
import colors
from commands.checks import owner_check

command = {
    "name": "lockdown",
    "aliases": ["ld"],
    "description": "Terminates bot usage for everyone except the owner",
}

class Lockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lockdown = False

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def lockdown(self, ctx):
        if not self.lockdown:
            self.bot.add_check(owner_check)
            await ctx.send(embed=Embed(
                title=":rotating_light: Lockdown Initiated :rotating_light:",
                description="Users will be unable to use commands during this time",
                color=colors.error,
            ))
            self.lockdown = True
        else:
            self.bot.remove_check(owner_check)
            await ctx.send(embed=Embed(
                title="Lockdown Ended",
                description="Users may now use commands again",
                color=colors.success,
            ))
            self.lockdown = False

async def setup(bot):
    await bot.add_cog(Lockdown(bot))