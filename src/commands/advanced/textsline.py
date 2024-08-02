from discord.ext import commands

import commands.locks as locks
from commands.advanced.raceline import get_args, run
from commands.basic.realspeedaverage import command_in_use
from database.bot_users import get_user
from utils import embeds

command = {
    "name": "textsline",
    "aliases": ["tl"],
    "description": "Displays a graph of user's texts typed over time",
    "parameters": "<date> [username] <username_2> ... <username_10> <date>",
    "usages": [
        "textsline rektless",
        "textsline 2023-09-01 clergy",
        "textsline 2024-01-01 keegant 2024-06-01",
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

            result = get_args(user, args, command)
            if embeds.is_embed(result):
                return await ctx.send(embed=result)

            usernames, start_date, end_date = result
            await run(ctx, user, usernames, start_date, end_date, column="text_id")


async def setup(bot):
    await bot.add_cog(TextsLine(bot))
