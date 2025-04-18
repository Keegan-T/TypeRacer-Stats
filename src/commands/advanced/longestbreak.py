import math

from discord import Embed
from discord.ext import commands

from commands.basic.stats import get_args
from database import users, races
from utils import errors, embeds, strings
from database.bot_users import get_user


command = {
    "name": "longestbreak",
    "aliases": ["pastashapes", "pasta", "break"],
    "description": "Displays the longest break between two races on a user's account",
    "parameters": "[username]",
    "usages": ["longestbreak pastashapes"],
}

class LongestBreak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def commandname(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)

async def run(ctx, user, username):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    era_string = strings.get_era_string(user)

    race_list = await races.get_races(username, ["number", "timestamp"], universe=universe)
    if not race_list:
        return await ctx.send(embed=errors.no_races(universe), content=era_string)
    race_list.sort(key=lambda x: x[1])

    longest_break = [0, {}]
    for i in range(1, len(race_list)):
        prev_race = race_list[i - 1]
        race = race_list[i]
        difference = race[1] - prev_race[1]
        if difference > longest_break[0]:
            longest_break = [difference, prev_race]

    description = (
        f"{strings.format_duration_short(math.floor(longest_break[0]))}\n"
        f"Starting on race {longest_break[1][0]:,}"
    )

    embed = Embed(
        title="Longest Break",
        description=description,
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)

async def setup(bot):
    await bot.add_cog(LongestBreak(bot))