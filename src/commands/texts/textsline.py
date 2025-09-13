from discord.ext import commands

import commands.locks as locks
from commands.graphs.raceline import get_args, run
from database.bot.users import get_user
from utils import embeds, dates
from utils.errors import command_in_use

command = {
    "name": "textsline",
    "aliases": ["tl"],
    "description": "Displays a graph of user's texts typed over time",
    "parameters": "[username] <username_2> ... <username_10> <start_date> <end_date>",
    "usages": [
        "textsline rektless",
        "textsline clergy 2023-09-01",
        "textsline keegant 2024-01-01 2024-06-01",
        "textsline rektless clergy charlieog keegant xanderec",
    ],
}


class TextsLine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textsline(self, ctx, *args):
        if locks.line_lock.locked():
            return await ctx.send(embed=command_in_use())

        async with locks.line_lock:
            user = get_user(ctx)
            args, user = dates.set_command_date_range(args, user)

            result = get_args(user, args, command)
            if embeds.is_embed(result):
                return await ctx.send(embed=result)

            await run(ctx, user, result, column="text_id")


async def setup(bot):
    await bot.add_cog(TextsLine(bot))
