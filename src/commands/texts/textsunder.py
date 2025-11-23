from discord.ext import commands

from commands.texts.textsover import run, get_args
from config import prefix
from database.bot.users import get_user
from utils import embeds, strings, dates

command = {
    "name": "textsunder",
    "aliases": ["tu", "tur"],
    "description": "Displays the number of texts a user has less than a category threshold\n"
                   f"Use `{prefix}tur` to randomize the results",
    "parameters": "[username] [threshold] <category> <sort>",
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
        args, user = dates.set_command_date_range(args, user)
        args, user = strings.set_wpm_metric(args, user)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, threshold, category, sort = result
        if ctx.invoked_with.lower() == "tur":
            sort = "random"
        await run(ctx, user, username, threshold, category, sort, over=False)


async def setup(bot):
    await bot.add_cog(TextsUnder(bot))
