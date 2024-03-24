from discord.ext import commands
from src.config import prefix
from database.bot_users import get_user
from commands.basic.realspeedaverage import get_params, run, command_in_use
from commands.locks import average_lock

info = {
    "name": "rawspeedaverage",
    "aliases": ["rawsa"],
    "description": "Displays raw speeds over a race interval\n"
                   "Capped at 10 races\n"
                   f"`{prefix}rawspeedaverage [username] <n>` returns the average for the last n races",
    "parameters": "[username] <first_race> <last_race>",
    "usages": [
        "rawspeedaverage keegant 5",
        "rawspeedaverage keegant 101 110"
    ],
    "import": False,
    "multiverse": True,
}


class RawSpeedAverage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def rawspeedaverage(self, ctx, *params):
        if average_lock.locked():
            self.rawspeedaverage.reset_cooldown(ctx)
            return await ctx.send(embed=command_in_use())

        async with average_lock:
            user = get_user(ctx)

            try:
                username, start_number, end_number, universe = await get_params(ctx, user, params, info)
            except ValueError:
                self.rawspeedaverage.reset_cooldown(ctx)
                return

            await run(ctx, user, username, start_number, end_number, universe, True)


async def setup(bot):
    await bot.add_cog(RawSpeedAverage(bot))
