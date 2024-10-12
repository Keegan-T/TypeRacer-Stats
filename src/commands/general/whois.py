from discord import Embed
from discord.ext import commands

from database import bot_users
from utils import errors, embeds, colors, strings, urls
from database.bot_users import get_user


command = {
    "name": "whois",
    "aliases": ["who"],
    "description": "Displays bot information about a user",
    "parameters": "[discord_id]",
    "usages": ["whois 155481579005804544"],
}

class WhoIs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def whois(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            return await ctx.send(embed=errors.missing_argument(command))

        user_id = args[0].translate(args[0].maketrans("", "", "<@>"))

        try:
            await self.bot.fetch_user(user_id)
        except:
            return await ctx.send(embed=Embed(title="Unknown User", color=colors.error))

        await run(ctx, user, str(user_id))

async def run(ctx, user, user_id):
    user_info = bot_users.get_user(user_id)
    username = user_info["username"]
    commands_used = sum([count for count in user_info["commands"].values()])
    top_commands = sorted(user_info["commands"].items(), key=lambda x: x[1], reverse=True)
    favorite_commands = "\n".join([f"{i + 1}. {command[0]} ({command[1]:,})" for i, command in enumerate(top_commands[:3])])

    name_string = f"<@{user_id}>"
    if user_info["username"]:
        name_string += f" ([{username}]({urls.profile(username, user['universe'])}))"

    description = (
        f"{name_string}\n\n"
        f"First Command: {strings.discord_timestamp(user_info['joined'], 'D')}\n"
        f"Commands Used: {commands_used:,}\n"
        f"{favorite_commands}\n"
    )

    embed = Embed(
        title=f"Who Is",
        description=description,
        color=user_info["colors"]["embed"],
    )

    await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(WhoIs(bot))