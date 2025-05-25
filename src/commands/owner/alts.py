from discord import Embed
from discord.ext import commands

import database.main.alts as alts
from api.users import get_stats
from commands.checks import owner_check
from database.bot.users import get_user
from utils import strings, errors

command = {
    "name": "alts",
    "aliases": ["alt"],
    "description": "Displays a list of alt accounts or updates the list\n",
    "usages": [
        "alts",
        "alts username",
        "alts add new_username existing_username",
        "alts remove username",
    ]
}


class Alts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def alts(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return await display_all(ctx, user)

        if args[0] == "add":
            await add(ctx, user, args[1], args[2])
        elif args[0] == "remove":
            await remove(ctx, user, args[1])
        else:
            await display(ctx, user, args[0])


async def display_all(ctx, user):
    groups = alts.get_groups()
    description = ""
    for group in groups:
        usernames = group["usernames"].split(",")
        usernames.sort()
        usernames = ", ".join(usernames)
        description += usernames + "\n\n"

    await send_embed(ctx, user, description)


async def display(ctx, user, username):
    alt_list = alts.get_username_alts(username)
    if not alt_list:
        description = "This account has no alts"
    else:
        description = ", ".join(alt_list)

    await send_embed(ctx, user, description)


async def add(ctx, user, new_username, existing_username):
    stats = get_stats(new_username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())
    success = alts.add_alt(new_username, existing_username)
    if not success:
        alt_list = ", ".join(alts.get_username_alts(new_username))
        description = f"{new_username} is already part of:\n{alt_list}"
        return await send_embed(ctx, user, description)

    alt_list = ", ".join(alts.get_username_alts(new_username))
    description = f"Added {new_username} to:\n{alt_list}"
    await send_embed(ctx, user, description)


async def remove(ctx, user, username):
    alts.remove_alt(username)

    description = f"Removed {username} for alts"

    await send_embed(ctx, user, description)


async def send_embed(ctx, user, description):
    embed = Embed(
        title="Alt Accounts",
        description=strings.escape_formatting(description),
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Alts(bot))
