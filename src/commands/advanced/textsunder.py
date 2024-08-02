from discord.ext import commands

from commands.advanced.textsover import run, get_args
from database.bot_users import get_user
from utils import embeds

command = {
    "name": "textsunder",
    "aliases": ["tu", "tur"],
    "description": "Displays the number of texts a user has less than a category threshold\n"
                   "Add `random` as a parameter to randomize the order in which races are displayed",
    "parameters": "[username] [threshold] <category>",
    "defaults": {
        "category": "wpm",
    },
    "usages": [
        "textsunder joshua728 1000 points",
        "textsunder charlieog 5000 times",
        "textsunder keegant 200 wpm random",
    ],
}


class TextsUnder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textsunder(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, threshold, category = result
        random = args[-1] in ["random", "rand", "r"] or ctx.invoked_with.lower() == "tur"
        await run(ctx, user, username, threshold, category, over=False, random=random)


async def setup(bot):
    await bot.add_cog(TextsUnder(bot))
