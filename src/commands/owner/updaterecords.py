from discord import Embed
from discord.ext import commands

from commands.checks import owner_check
from database import records
from database.bot_users import get_user
from records import update_all as update, update_section

command = {
    "name": "updaterecords",
    "aliases": ["records", "record", "rec"],
    "description": "Updates the record list",
}


class UpdateRecords(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def updaterecords(self, ctx, *args):
        if not args:
            return

        user = get_user(ctx)

        if args[0] in ["reload"]:
            return await update_all(ctx, user, self.bot)

        await update_record(ctx, user, self.bot, *args)


async def update_record(ctx, user, bot, category, index, username, record, date, link):
    name = records.update_record(category, index, username, record, date, link)

    await update_section(bot, category)

    embed = Embed(
        title="Records",
        description=f"Updated {name}",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def update_all(ctx, user, bot):
    await ctx.send(embed=Embed(
        title="Records Update Request",
        description="Updating records channel",
        color=user["colors"]["embed"],
    ))

    await update(bot)

    await ctx.send(embed=Embed(
        title="Records Update Request",
        description="Finished updating records channel",
        color=user["colors"]["embed"],
    ))


async def setup(bot):
    await bot.add_cog(UpdateRecords(bot))
