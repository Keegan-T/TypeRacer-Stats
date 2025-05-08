from collections import Counter
from statistics import mode

import numpy as np
from discord.ext import commands

import database.races as races
import database.users as users
from database.bot_users import get_user
from graphs import histogram
from utils import errors, colors, embeds, strings
from utils.embeds import Page, Message

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
    era_string = strings.get_era_string(user)

    race_list = await races.get_races(
        username, columns=["wpm", "accuracy"], universe=universe,
        start_date=user["start_date"], end_date=user["end_date"]
    )

    if len(race_list) == 0:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    def file_name(category):
        return f"histogram_{username}_{category}.png"

    wpm_values = [race[0] for race in race_list]
    distribution_stats = get_distribution_stats(wpm_values, " WPM")

    def render_wpm(file_name):
        histogram.render(
            user, username, wpm_values, "WPM", "WPM", "auto", file_name, universe
        )

    wpm_page = Page(
        title="WPM Histogram",
        description=distribution_stats,
        default=category == "wpm",
        button_name="WPM",
        render=render_wpm,
        file_name=file_name("wpm"),
    )

    accuracy_values = [int(race[1] * 100) for race in race_list if race[1] > 0]

    def render_accuracy(file_name):
        values = np.array(accuracy_values)
        values = values[values >= 90]
        bins = np.arange(min(values), 102, 1)
        histogram.render(
            user, username, accuracy_values, "Accuracy", "Accuracy %", bins, file_name, universe
        )

    if not accuracy_values:
        accuracy_page = Page(
            title="Missing Information",
            description="Account has no registered accuracies above 0%",
            default=category == "accuracy",
            color=colors.error,
            button_name="Accuracy",
        )
    else:
        distribution_stats = get_distribution_stats(accuracy_values, "%")
        accuracy_page = Page(
            title="Accuracy Histogram",
            description=distribution_stats,
            default=category == "accuracy",
            footer="Due to accuracy being rounded in the API, data is not exactly as it appears\n"
                   "(i.e., data in the 99% bin include values 98.5% - 99.5%)",
            button_name="Accuracy",
            render=render_accuracy,
            file_name=file_name("accuracy"),
        )

    if era_string:
        text_bests = await users.get_text_bests_time_travel(username, universe, user)
    else:
        text_bests = users.get_text_bests(username, universe=universe)
    text_best_values = [race[1] for race in text_bests]
    distribution_stats = get_distribution_stats(text_best_values, " WPM")

    def render_text_bests(file_name):
        histogram.render(
            user, username, text_best_values, "Text Bests", "Text Bests", "auto", file_name, universe
        )

    text_bests_page = Page(
        title="Text Bests Histogram",
        description=distribution_stats,
        default=category == "textbests",
        button_name="Text Bests",
        render=render_text_bests,
        file_name=file_name("text_bests"),
    )

    pages = [wpm_page, text_bests_page, accuracy_page]
    message = Message(
        ctx, user, pages,
        profile=stats,
        universe=universe,
    )

    await message.send()


def get_distribution_stats(values, suffix):
    value_array = np.array(values)
    mean = np.mean(values)
    median = np.median(values)
    mode_value = mode(values)
    mode_frequency = Counter(values)[mode_value]
    std = np.std(value_array)

    return (
        f"**Average:** {mean:,.2f}{suffix}\n"
        f"**Median:** {median:,.2f}{suffix}\n"
        f"**Mode:** {mode_value:,.2f}{suffix} ({mode_frequency:,} times)\n"
        f"**Range:** {max(values) - min(values):,.2f} ({min(values):,.2f}{suffix} - {max(values):,.2f}{suffix})\n"
        f"**Standard Deviation:** {std:,.2f}{suffix}\n"
    )


async def setup(bot):
    await bot.add_cog(Histogram(bot))
