import urllib.parse

import requests
from discord import Embed
from discord.ext import commands

from database.bot_users import get_user
from utils import errors, strings, colors

command = {
    "name": "calculator",
    "aliases": ["calc", "eval", "math"],
    "description": "Evaluates a mathematical expression",
    "parameters": "[expression]",
    "usages": ["calculator 1 + 1"],
}


class Calculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def calculator(self, ctx, *args):
        if not args:
            return await ctx.send(embed=errors.missing_argument(command))

        user = get_user(ctx)
        expression = " ".join(args)

        await run(ctx, user, expression)


async def run(ctx, user, expression):
    expression = urllib.parse.quote(expression)
    try:
        url = f"https://api.mathjs.org/v4/?expr={expression}"
        response = requests.get(url)
        text = response.text
        if "Error" in text:
            raise ValueError

        answer = []
        for string in text.split(" "):
            try:
                answer.append(strings.format_expression(float(string)))
            except ValueError:
                answer.append(string)
        final = " ".join(answer)
    except ValueError:
        return await ctx.send(embed=Embed(
            title="Invalid Expression",
            description="Expression format is invalid",
            color=colors.error,
        ))

    embed = Embed(
        title="Calculator",
        description=f"```{final}```",
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Calculator(bot))
