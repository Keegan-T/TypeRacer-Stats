from discord import Embed
from discord.ext import commands
import errors
from database.bot_users import get_user
import database.texts as texts
from commands.checks import owner_check

command = {
    "name": "toggletext",
    "aliases": ["textenable", "te", "textdisable", "td"],
    "description": "Enables/disabled texts",
}


class ToggleText(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def toggletext(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return await ctx.send(embed=errors.unknown_text())

        text_id = args[0]

        await run(ctx, user, text_id)


async def run(ctx, user, text_id):
    text = texts.get_text(text_id)
    if not text:
        return await ctx.send(embed=errors.unknown_text())

    status = "Disabled"
    if ctx.invoked_with in ["textdisable", "td"]:
        texts.disable_text(text_id)
    else:
        status = "Enabled"
        await texts.enable_text(text_id)

    embed = Embed(
        title=f"{status} Text #{text_id}",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ToggleText(bot))
