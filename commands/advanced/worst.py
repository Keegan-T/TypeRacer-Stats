from discord.ext import commands
from database.bot_users import get_user
from commands.advanced.best import get_params, run, categories

info = {
    "name": "worst",
    "aliases": ["bottom"],
    "description": "Displays a user's bottom 10 worst races in a given category\n"
                   "Provide a text ID to see best races for a specific text",
    "parameters": "[username] <category/text_id>",
    "defaults": {
        "category": "wpm",
    },
    "usages": [f"worst keegant {category}" for category in categories],
    "import": True,
}


class Worst(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def worst(self, ctx, *params):
        user = get_user(ctx)
        try:
            username, category, text_id = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, category, text_id, False)


async def setup(bot):
    await bot.add_cog(Worst(bot))
