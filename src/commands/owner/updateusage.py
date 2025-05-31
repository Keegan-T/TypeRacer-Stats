from discord import Embed
from discord.ext import commands

from commands.checks import owner_check
from commands.info.help import command_dict
from database.bot import users
from database.bot.users import get_user
from utils import colors, errors, strings

command = {
    "name": "updateusage",
    "aliases": ["uu"],
    "description": "Updates a user's command usage",
    "parameters": "[discord_id] [command] [number]",
    "usages": ["updateusage 155481579005804544 thonk 100000"],
}


class UpdateUsage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    @commands.check(owner_check)
    async def updateusage(self, ctx, *args):
        user = get_user(ctx)

        if len(args) < 3:
            return await ctx.send(embed=errors.missing_argument(command))

        user_id = strings.get_discord_id(args[0])
        if not user_id:
            return await ctx.send(embed=Embed(title="Invalid User", color=colors.error))

        command_name = args[1]
        if command_name not in command_dict:
            return await ctx.send(embed=errors.invalid_command())

        new_number = int(args[2])
        await run(ctx, user, user_id, command_dict[command_name]["name"], new_number)


async def setup(bot):
    await bot.add_cog(UpdateUsage(bot))


async def run(ctx, user, user_id, command_name, new_number):
    users.update_commands(user_id, command_name, value=new_number)

    embed = Embed(
        title=f"Command Usage Updated",
        description=f"Set command usage of `{command_name}` to {new_number:,} for <@{user_id}>",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)
