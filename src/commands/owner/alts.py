from discord import Embed
from discord.ext import commands

import database.alts as alts
from commands.checks import owner_check
from database.bot_users import get_user
from utils import strings

command = {
    "name": "alts",
    "aliases": ["alt"],
    "description": "Displays a list of alt accounts or updates the list",
}


class Alts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def alts(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return await display(ctx, user)

        if args[0] == "add":
            await add(ctx, user, args[1], args[2])
        elif args[0] == "remove":
            await remove(ctx, user, args[1])


async def display(ctx, user):
    alt_list = alts.get_alts()

    groups = {frozenset(group) for group in alt_list.values()}
    description = "\n".join(", ".join(group) for group in groups)

    await send_embed(ctx, user, description)


async def add(ctx, user, main_username, alt_username):
    alts.add_alt(main_username, alt_username)

    alt_list = alts.get_alts()
    group = alt_list[main_username]
    description = f"Added {strings.escape_discord_format(alt_username)} to:\n" + ", ".join(group)

    await send_embed(ctx, user, description)


async def remove(ctx, user, username):
    alts.remove_alt(username)

    description = f"Removed {username} for alts"

    await send_embed(ctx, user, description)


async def send_embed(ctx, user, description):
    embed = Embed(
        title="Alt Accounts",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Alts(bot))
