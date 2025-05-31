import importlib
import os

from discord import Embed
from discord.ext import commands

from config import prefix, bot_admins, bot_owner
from database.bot.users import get_user
from utils import errors

groups = ["account", "advanced", "basic", "general", "info", "admin", "owner"]
command = {
    "name": "help",
    "aliases": ["h"],
    "description": "Displays a list of available commands, or information about a specific command",
    "parameters": "<command>",
    "usages": ["help", "help stats"],
}


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def help(self, ctx, *args):
        user = get_user(ctx)
        if not args:
            return await help_main(ctx, user)

        command_dict = get_command_dict()
        command_name = args[0]
        if command_name not in command_dict:
            return await ctx.send(embed=errors.invalid_command())

        await help_command(ctx, user, command_dict[command_name])


async def help_main(ctx, user):
    embed = Embed(
        title="Help Page",
        description=f"`{prefix}help` - Displays this message\n"
                    f"`{prefix}help [command]` - Displays help for a specific command\n"
                    f"`[ ]` represents required parameters\n"
                    f"`< >` represents optional parameters",
        color=user["colors"]["embed"],
    )

    command_list = {}

    for group in groups:
        command_list[group] = []
        for file in os.listdir(f"./commands/{group}"):
            if file.endswith(".py") and not file.startswith("_") and not file.startswith("help"):
                command_list[group].append(file[:-3])

    for key in command_list.keys():
        command_list[key].sort(key=lambda x: x[0])

    account_commands = ", ".join(f"`{cmd}`" for cmd in command_list["account"])
    info_commands = ", ".join(f"`{cmd}`" for cmd in command_list["info"])
    general_commands = ", ".join(f"`{cmd}`" for cmd in command_list["general"])
    basic_commands = ", ".join(f"`{cmd}`" for cmd in command_list["basic"])
    advanced_commands = ", ".join(f"`{cmd}`" for cmd in command_list["advanced"])
    admin_commands = ", ".join(f"`{cmd}`" for cmd in command_list["admin"])
    owner_commands = ", ".join(f"`{cmd}`" for cmd in command_list["owner"])

    embed.add_field(name="Account Commands", value=account_commands, inline=False)
    embed.add_field(name="Info Commands", value=info_commands, inline=False)
    embed.add_field(name="General Commands", value=general_commands, inline=False)
    embed.add_field(name="Basic User Commands", value=basic_commands, inline=False)
    embed.add_field(name=f"Advanced User Commands (`{prefix}import` required)", value=advanced_commands, inline=False)
    if ctx.author.id in bot_admins:
        embed.add_field(name="Admin Commands", value=admin_commands, inline=False)
    if ctx.author.id == bot_owner:
        embed.add_field(name="Owner Commands", value=owner_commands, inline=False)

    embed.set_footer(text="Developed by keegant", icon_url="https://cdn.discordapp.com/avatars/155481579005804544/33ede24295683bbb2253481d5029266e.webp?size=1024")

    await ctx.send(embed=embed)


async def help_command(ctx, user, command_info):
    name = command_info["name"]
    aliases = command_info["aliases"]

    embed = Embed(
        title=f"Help for `{prefix}{name}`",
        description=command_info['description'],
        color=user["colors"]["embed"]
    )

    if "parameters" in command_info:
        parameter_string = f"`{prefix}{name} {command_info['parameters']}`"
        if "defaults" in command_info:
            for param, default in command_info["defaults"].items():
                parameter_string += f"\n`{param}` defaults to {default}"
        embed.add_field(
            name="Parameters",
            value=parameter_string,
            inline=False,
        )

    if "usages" in command_info:
        embed.add_field(
            name="Usage",
            value="\n".join([f"`{prefix}{usage}`" for usage in command_info['usages']]),
            inline=False,
        )

    if aliases:
        embed.add_field(
            name="Aliases",
            value=", ".join([f"`{prefix}{alias}`" for alias in command_info['aliases']]),
            inline=False
        )

    footer_text = ""
    if "multiverse" in command_info:
        footer_text += "This command does not work in the multiverse"

    if "temporal" in command_info:
        footer_text += "\nThis command cannot be manipulated by time"

    if footer_text:
        embed.set_footer(text=footer_text)

    await ctx.send(embed=embed)


def get_command_dict():
    command_dict = {}
    for group in groups:
        for file in os.listdir(f"./commands/{group}"):
            if file.endswith(".py") and not file.startswith("_"):
                module = importlib.import_module(f"commands.{group}.{file[:-3]}")
                command_info = module.command
                for alias in [command_info["name"]] + command_info["aliases"]:
                    command_dict[alias] = command_info

    return command_dict


async def setup(bot):
    await bot.add_cog(Help(bot))
