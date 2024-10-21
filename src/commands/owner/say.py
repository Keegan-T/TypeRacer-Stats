from discord.ext import commands

from commands.checks import owner_check

command = {
    "name": "say",
    "aliases": [],
    "description": "Sends a message in #typeracer-stats",
    "parameters": "[message]",
    "usages": ["say hi"],
}


class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def say(self, ctx, *args):
        if not args:
            return

        message = " ".join(args)
        typeracer_stats_channel = 746460695670816798
        channel = self.bot.get_channel(typeracer_stats_channel)

        await channel.send(message)


async def setup(bot):
    await bot.add_cog(Say(bot))
