from discord.ext import commands
from database.bot_users import get_user
from commands.advanced.textsover import run, get_params

info = {
    "name": "textsunder",
    "aliases": ["tu"],
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
    "import": True,
}


class TextsUnder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def textsunder(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, threshold, category, random = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, threshold, category, over=False, random=random)


async def setup(bot):
    await bot.add_cog(TextsUnder(bot))
