from discord import Embed
from discord.ext import commands
import importlib
import os
import utils
import errors
import colors
from config import prefix
from database.bot_users import get_user, get_commands, get_all_commands, get_total_commands

command = {
    "name": "commandleaderboard",
    "aliases": ["clb"],
    "description": "Displays command usage stats for a specific user or command\n"
                   f"`{prefix}commandleaderboard all` will show most used commands overall",
    "parameters": "[discord_id/command]",
    "defaults": {
        "discord_id": "your discord ID",
    },
    "usages": [
        "commandleaderboard @keegant",
        "commandleaderboard 155481579005804544",
        "commandleaderboard stats"
    ],
}


class CommandLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def commandleaderboard(self, ctx, *args):
        user = get_user(ctx)

        discord_id = ctx.author.id

        if args:
            discord_id = utils.get_discord_id(args[0])
            if discord_id:
                return await user_leaderboard(ctx, user, discord_id)
            elif args[0] == "all":
                return await user_leaderboard(ctx, user, "all")

            command_name = args[0]
            return await command_leaderboard(ctx, user, command_name)

        return await user_leaderboard(ctx, user, discord_id)


async def command_leaderboard(ctx, user, name):
    alias_dict = {}

    groups = ["account", "admin", "advanced", "basic", "general", "info", "owner", "unlisted"]
    for group in groups:
        for file in os.listdir(f"./commands/{group}"):
            if file.endswith(".py") and not file.startswith("_"):
                module = importlib.import_module(f"commands.{group}.{file[:-3]}")
                command_name = module.command["name"]
                aliases = [command_name] + module.command["aliases"]
                for alias in aliases:
                    alias_dict[alias] = command_name

    if name not in alias_dict:
        return await ctx.send(embed=errors.invalid_command())

    name = alias_dict[name]
    all_commands = get_all_commands()

    command_usage = []
    total_usages = 0
    for bot_user in all_commands:
        user_commands = bot_user["commands"]
        if name in user_commands:
            command_usage.append(bot_user)
            total_usages += user_commands[name]
    sorted_usage = sorted(command_usage, key=lambda x: x["commands"][name], reverse=True)

    description = ""
    for i, bot_user in enumerate(sorted_usage[:10]):
        description += f"{i + 1}. <@{bot_user['id']}> - {bot_user['commands'][name]:,}\n"

    embed = Embed(
        title=f"Usage Leaderboard - {name}",
        description=description,
        color=user["colors"]["embed"],
    )
    embed.set_footer(text=f"Total Usages: {total_usages:,}")

    await ctx.send(embed=embed)


async def user_leaderboard(ctx, user, discord_id):
    if discord_id == "all":
        command_usage = get_total_commands()
        description = "**Overall**\n\n"
    else:
        command_usage = get_commands(discord_id)
        if not command_usage:
            return await ctx.send(embed=no_commands(discord_id))
        description = f"<@{discord_id}>\n\n"

    total_usages = sum([command[1] for command in command_usage.items()])
    most_used_commands = sorted(command_usage.items(), key=lambda x: x[1], reverse=True)
    for i, command_info in enumerate(most_used_commands[:10]):
        name, usages = command_info
        description += f"{i + 1}. {name} - {usages:,}\n"

    embed = Embed(
        title=f"Most Used Commands",
        description=description,
        color=user["colors"]["embed"],
    )
    embed.set_footer(text=f"Total Usages: {total_usages:,}")

    await ctx.send(embed=embed)


def no_commands(discord_id):
    return Embed(
        title="No Commands Used",
        description=f"<@{discord_id}> has not used any commands",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(CommandLeaderboard(bot))
