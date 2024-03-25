from discord import Embed
from discord.ext import commands
from database.bot_users import get_user
from config import bot_admins, supporters

info = {
    "name": "about",
    "aliases": ["info"],
    "description": "Displays information about the bot",
}

class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def about(self, ctx,):
        user = get_user(ctx)

        await run(ctx, user)

async def run(ctx, user):
    bot_admins_list = ", ".join([f"<@{admin}>" for admin in bot_admins[1:]])
    supporter_list = ", ".join([f"<@{supporter}>" for supporter in supporters])

    description = (
        "<@1213306973374644256> is an extensive <:typeracer_logo:1219587776308183060> [TypeRacer](https://play.typeracer.com/) statistics bot designed to enhance the TypeRacer experience. It is a rewrite of the popular <@742267194443956334> by <@697048255254495312>, providing a handful of new commands and features.\n\n"
        "Developed by <@155481579005804544>, written in <:python_logo:1219588087383064647> Python.\n\n"
        f"**Supporters** <:support:1220863071086575716>\n{supporter_list}\n\n"
        f"**Bot Admins**\n{bot_admins_list}\n"
    )


    embed = Embed(
        title="TypeRacer Stats",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(About(bot))