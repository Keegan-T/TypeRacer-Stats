from discord import Embed
from discord.ext import commands

from config import bot_owner
from utils import files

message_path = "data/message.txt"
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
    embed = Embed(
        description=files.read_file(message_path),
        color=0,
    )

    await ctx.send(embed=embed)


async def update_message(ctx, message):
    files.write_file(message_path, message)

    await run(ctx)


async def setup(bot):
    await bot.add_cog(Keegan(bot))
