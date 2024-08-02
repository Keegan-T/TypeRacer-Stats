from collections import Counter
from statistics import mode

import numpy as np
from discord import Embed, File
from discord.ext import commands

import database.races as races
import database.users as users
from database.bot_users import get_user
from graphs import histogram
from graphs.core import remove_file
from utils import errors, colors, embeds, strings

categories = ["wpm", "accuracy", "textbests"]
command = {
    "name": "histogram",
    "aliases": ["hist", "hg"],
    "description": "Displays a histogram and relevant stats for a category",
    "parameters": "[username] <category>",
    "defaults": {
        "category": "wpm"
    },
    "usages": [
        "histogram keegant wpm",
        "histogram skyprompdvorak accuracy",
        "histogram joshua728 textbests"
    ],
}


class Histogram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def histogram(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, category = result

        await run(ctx, user, username, category)


def get_args(user, args, info):
    params = f"username category:{'|'.join(categories)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, category):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    category_title = "WPM"
    suffix = " WPM"

    if category == "wpm":
        race_list = await races.get_races(username, columns=["wpm"], universe=universe)
        values = [race[0] for race in race_list]

    elif category == "textbests":
        race_list = users.get_text_bests(username, universe=universe)
        values = [race[1] for race in race_list]
        category_title = "Text Bests"

    else:
        race_list = await races.get_races(username, columns=["accuracy"], universe=universe)
        values = [int(race[0] * 100) for race in race_list if race[0] > 0]
        category_title = "Accuracy"
        suffix = "%"

    if not values:
        return await ctx.send(embed=missing_info())

    value_array = np.array(values)
    mean = np.mean(values)
    median = np.median(values)
    mode_value = mode(values)
    mode_frequency = Counter(values)[mode_value]
    std = np.std(value_array)

    distribution_stats = (
        f"**Average:** {mean:,.2f}{suffix}\n"
        f"**Median:** {median:,.2f}{suffix}\n"
        f"**Mode:** {mode_value:,.2f}{suffix} ({mode_frequency:,} times)\n"
        f"**Range:** {max(values) - min(values):,.2f} ({min(values):,.2f}{suffix} - {max(values):,.2f}{suffix})\n"
        f"**Standard Deviation:** {std:,.2f}{suffix}\n"
    )

    embed = Embed(
        title=f"{category_title} Histogram",
        description=distribution_stats,
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, stats, universe)

    file_name = f"histogram_{username}_{category}.png"
    histogram.render(user, username, values, category, file_name, universe)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    if category == "accuracy":
        embed.set_footer(
            text="Due to accuracy being rounded in the API, data is not exactly as it appears\n"
                 "(i.e., data in the 99% bin include values 98.5% - 99.5%)"
        )
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, file=file)

    remove_file(file_name)


def missing_info():
    return Embed(
        title="Missing Information",
        description="Account has no registered accuracies above 0%",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Histogram(bot))
