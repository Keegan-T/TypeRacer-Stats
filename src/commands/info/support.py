from discord import Embed
from discord.ext import commands

from config import donate_link
from database.bot_users import get_user

command = {
    "name": "support",
    "aliases": ["donate"],
    "description": "Show your support for TypeRacer Stats <:support:1220863071086575716>",
}


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def support(self, ctx):
        user = get_user(ctx)

        await run(ctx, user)


async def run(ctx, user):
    description = (
        "TypeRacer Stats is hosted out of pocket to provide 24/7 availability for the community.\n"
        "One month of hosting costs $12.00 USD\n\n"
        f"[Click here to donate]({donate_link})\n"
        f"Thank you for your support! <:support:1220863071086575716>"
    )

    embed = Embed(
        title="Support TypeRacer Stats",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Support(bot))
