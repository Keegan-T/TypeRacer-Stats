import os

from discord import Embed
from discord.ext import commands

from config import bot_owner, root_dir

message_path = os.path.join(root_dir, "src", "data", "message.txt")
command = {
    "name": "keegan",
    "aliases": ["keegant", "kegnat", "kt"],
    "description": "keegan",
}


class Keegan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def keegan(self, ctx, *args):
        if args and ctx.author.id == bot_owner:
            message = " ".join(args)
            return await update_message(ctx, message)

        await run(ctx)


async def run(ctx):
    with open(message_path, "r", encoding="utf-8") as file:
        message = "".join(file.readlines())

    embed = Embed(
        description=message,
        color=0,
    )

    await ctx.send(embed=embed)


async def update_message(ctx, message):
    with open(message_path, "w", encoding="utf-8") as file:
        file.writelines(message)

    await run(ctx)


async def setup(bot):
    await bot.add_cog(Keegan(bot))
