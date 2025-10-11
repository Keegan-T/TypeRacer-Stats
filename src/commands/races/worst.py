from discord.ext import commands

from commands.races.best import get_args, run, categories
from database.bot.users import get_user
from utils import embeds, strings

command = {
    "name": "worst",
    "aliases": ["bottom"],
    "description": "Displays a user's bottom 10 worst races in a given category\n"
                   "Provide a text ID to see best races for a specific text",
    "parameters": "[username] <category/text_id>",
    "defaults": {
        "category": "wpm",
    },
    "usages": [f"worst keegant {category}" for category in categories],
}


class Worst(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def worst(self, ctx, *args):
        user = get_user(ctx)
        args, user = strings.set_wpm_metric(args, user)

        result = get_args(user, args, command, ctx.channel.id)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, category, text_id = result
        await run(ctx, user, username, category, text_id, reverse=False)


async def setup(bot):
    await bot.add_cog(Worst(bot))
