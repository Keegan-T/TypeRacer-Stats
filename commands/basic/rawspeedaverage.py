from discord.ext import commands
from config import prefix
from database.bot_users import get_user
from commands.basic.realspeedaverage import get_args, run, command_in_use
import commands.locks as locks
import utils

command = {
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
}


class RawSpeedAverage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def rawspeedaverage(self, ctx, *args):
        if locks.average_lock.locked():
            self.rawspeedaverage.reset_cooldown(ctx)
            return await ctx.send(embed=command_in_use())

        async with locks.average_lock:
            user = get_user(ctx)

            result = get_args(user, args, command)
            if utils.is_embed(result):
                self.rawspeedaverage.reset_cooldown(ctx)
                return await ctx.send(embed=result)

            username, start_number, end_number = result
            universe = user["universe"]
            await run(ctx, user, username, start_number, end_number, universe, raw=True)


async def setup(bot):
    await bot.add_cog(RawSpeedAverage(bot))
