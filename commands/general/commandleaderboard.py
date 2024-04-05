from discord import Embed
from discord.ext import commands
import importlib
import os
import utils
import errors
import colors
from config import prefix
from database.bot_users import get_user, get_commands, get_all_commands, get_total_commands

info = {
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
    "import": False,
}


class CommandLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def commandleaderboard(self, ctx, *params):
        user = get_user(ctx)

        discord_id = ctx.author.id

        if params:
            discord_id = utils.get_discord_id(params[0])
            if discord_id:
                return await user_leaderboard(ctx, user, discord_id)
            elif params[0] == "all":
                return await user_leaderboard(ctx, user, "all")

            command = params[0]
            return await command_leaderboard(ctx, user, command)

        return await user_leaderboard(ctx, user, discord_id)


# POSSIBLE USAGES:
# 2. clb <command> - will display the top 10 users who have used this command the most
# 3. clb all - will display the top 10 most used commands overall
async def command_leaderboard(ctx, user, command):
    alias_dict = {}

    groups = ["account", "admin", "advanced", "basic", "general", "info", "owner", "unlisted"]
    for group in groups:
        for file in os.listdir(f"./commands/{group}"):
            if file.endswith(".py") and not file.startswith("_"):
                module = importlib.import_module(f"commands.{group}.{file[:-3]}")
                command_name = module.info["name"]
                aliases = [command_name] + module.info["aliases"]
                for alias in aliases:
                    alias_dict[alias] = command_name

    if command not in alias_dict:
        return await ctx.send(embed=errors.invalid_command())

    command = alias_dict[command]
    all_commands = get_all_commands()
    command_usage = [bot_user for bot_user in all_commands if command in bot_user["commands"]]
    sorted_usage = sorted(command_usage, key=lambda x: x["commands"][command], reverse=True)

    description = ""
    for i, bot_user in enumerate(sorted_usage[:10]):
        description += f"{i + 1}. <@{bot_user['id']}> - {bot_user['commands'][command]}\n"

    embed = Embed(
        title=f"Usage Leaderboard - {command}",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def user_leaderboard(ctx, user, discord_id):
    if discord_id == "all":
        total_commands = get_total_commands()
        most_used_commands = sorted(total_commands.items(), key=lambda x: x[1], reverse=True)

        description = "**Overall**\n\n"
        for i, command in enumerate(most_used_commands[:10]):
            name, usages = command
            description += f"{i + 1}. {name} - {usages}\n"

    else:
        user_commands = get_commands(discord_id)
        if not user_commands:
            return await ctx.send(embed=no_commands(discord_id))

        most_used_commands = sorted(user_commands.items(), key=lambda x: x[1], reverse=True)

        description = f"<@{discord_id}>\n\n"
        for i, command in enumerate(most_used_commands[:10]):
            name, usages = command
            description += f"{i + 1}. {name} - {usages}\n"

    embed = Embed(
        title=f"Most Used Commands",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


def no_commands(discord_id):
    return Embed(
        title="No Commands Used",
        description=f"<@{discord_id}> has not used any commands",
        color=colors.error,
    )



async def setup(bot):
    await bot.add_cog(CommandLeaderboard(bot))
