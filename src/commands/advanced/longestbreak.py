import math

from discord.ext import commands

from commands.basic.stats import get_args
from database.main import races, users
from database.bot.users import get_user
from utils import errors, strings
from utils.embeds import Page, Message, is_embed

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
    async def longestbreak(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)


async def run(ctx, user, username):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    era_string = strings.get_era_string(user)

    race_list = await races.get_races(
        username, ["number", "timestamp"], universe=universe,
        start_date=user["start_date"], end_date=user["end_date"]
    )
    if not race_list:
        return await ctx.send(embed=errors.no_races(universe), content=era_string)
    race_list.sort(key=lambda x: x[1])

    breaks = []
    for i in range(len(race_list) - 1):
        prev_race = race_list[i]
        race = race_list[i + 1]
        difference = race[1] - prev_race[1]
        breaks.append((i, difference))

    breaks.sort(key=lambda x: x[1], reverse=True)

    description = (
        f"{strings.format_duration(math.floor(breaks[0][1]))}\n"
        f"Starting on race {race_list[breaks[0][0]]['number']:,}"
    )

    top_description = ""
    for i, _break in enumerate(breaks[:10]):
        start_race, end_race = race_list[_break[0]:_break[0] + 2]
        top_description += (
            f"**{strings.discord_timestamp(start_race['timestamp'], 'D')} - "
            f"{strings.discord_timestamp(end_race['timestamp'], 'D')}**\n"
            f"{i + 1}. {strings.format_duration(math.floor(_break[1]))}"
            f" (Starting on Race {start_race['number']:,})\n\n"
        )

    pages = [
        Page(
            title="Longest Break",
            description=description,
            button_name="Longest",
        ),
        Page(
            title="Top 10 Longest Breaks",
            description=top_description,
            button_name="Top 10",
        )
    ]

    message = Message(
        ctx, user, pages,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(LongestBreak(bot))
