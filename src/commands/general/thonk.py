import random

from discord import File
from discord.ext import commands

from graphs.core import remove_file
from utils import embeds, strings
from utils.thonk import generate_thonk

command = {
    "name": "thonk",
    "aliases": [],
    "description": "Randomly generates a thonk emote",
    "parameters": "<seed>",
    "usages": ["thonk", "thonk 12345"],
}

class Thonk(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def thonk(self, ctx, *args):
        seed = None if not args else " ".join(args)
        await run(ctx, seed)

def get_args(user, args, info):
    params = "username"
    result = strings.parse_command(user, params, args, info)
    if embeds.is_embed(result):
        return result

    return result[0]

async def run(ctx, seed):
    if not seed:
        seed = str(random.randint(0, 1000000000))
    file_name = f"thonk_{seed}.png"
    generate_thonk(file_name, seed)

    file = File(file_name, filename=file_name)
    await ctx.send(content=f"-# Seed: {seed}", file=file)

    remove_file(file_name)

async def setup(bot):
    await bot.add_cog(Thonk(bot))