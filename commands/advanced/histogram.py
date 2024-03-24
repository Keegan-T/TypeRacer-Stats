from discord import Embed, File
from discord.ext import commands
import colors
import errors
import os
import graphs
import utils
from database.bot_users import get_user
import database.users as users
import database.races as races
import database.texts as texts
import numpy as np
from datetime import datetime, timezone
from scipy.stats import mode

categories = ["wpm", "accuracy", "textbests"]
info = {
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
    "import": True,
}


class Histogram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def histogram(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, category = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, category)


async def get_params(ctx, user, params):
    username = user["username"]
    category = "wpm"

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        category = utils.get_category(categories, params[1])
        if not category:
            await ctx.send(embed=errors.invalid_option("category", categories))
            raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), category


async def run_time(ctx, user, username):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    race_list = races.get_races(username, columns=["text_id", "wpm", "timestamp"], order_by="timestamp")
    text_list = texts.get_texts(as_dictionary=True)
    total_seconds = 0

    activity = [[stats["joined"], 0]]
    for race in race_list:
        text_id, wpm, timestamp = race

        while timestamp >= activity[-1][0] + 86400:
            activity.append([activity[-1][0] + 86400, 0])

        seconds = utils.calculate_seconds(text_list[text_id]["quote"], wpm)
        activity[-1][1] += seconds
        total_seconds += seconds

    average = total_seconds / len(activity)
    most_seconds = (0, 0)
    for day, seconds in activity:
        if seconds > most_seconds[1]:
            most_seconds = (day, seconds)

    description = (
        f"**Average Daily:** {utils.format_duration_short(average)}\n"
        f"**Most Active Day:** {datetime.fromtimestamp(most_seconds[0], tz=timezone.utc).strftime('%#m/%#d/%Y')} - "
        f"{utils.format_duration_short(most_seconds[1])}"
    )

    embed = Embed(
        title=f"Daily Activity Histogram",
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats)

    file_name = f"{username}_histogram.png"
    graphs.histogram_time(user, username, activity, file_name)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    os.remove(file_name)


async def run(ctx, user, username, category):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    category_title = "WPM"
    suffix = " WPM"

    if category == "wpm":
        race_list = races.get_races(username, columns=["wpm"])
        values = [race[0] for race in race_list]

    elif category == "textbests":
        race_list = users.get_text_bests(username)
        values = [race[1] for race in race_list]
        category_title = "Text Bests"

    else:
        race_list = races.get_races(username, columns=["accuracy"])
        values = [int(race[0] * 100) for race in race_list if race[0] > 0]
        category_title = "Accuracy"
        suffix = "%"

    if not values:
        return await ctx.send(embed=missing_info())

    value_array = np.array(values)
    mean = np.mean(values)
    median = np.median(values)
    mode_result = mode(values, keepdims=True)
    value_mode = mode_result[0][0]
    mode_frequency = mode_result[1][0]
    std = np.std(value_array)
    # wpm_skew = skew(value_array)
    # skew_string = ("Right" if wpm_skew < 0 else "Left") + f" by {abs(wpm_skew):,.2f} WPM"

    distribution_stats = (
        f"**Average:** {mean:,.2f}{suffix}\n"
        f"**Median:** {median:,.2f}{suffix}\n"
        f"**Mode:** {value_mode:,.2f}{suffix} ({mode_frequency:,} times)\n"
        f"**Range:** {max(values) - min(values):,.2f} ({min(values):,.2f}{suffix} - {max(values):,.2f}{suffix})\n"
        f"**Standard Deviation:** {std:,.2f}{suffix}\n"
        # f"**Skewness:** {skew_string}\n"
    )

    embed = Embed(
        title=f"{category_title} Histogram",
        description=distribution_stats,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats)

    file_name = f"histogram_{username}_{category}.png"
    graphs.histogram(user, username, values, category, file_name)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    if category == "accuracy":
        embed.set_footer(
            text="Due to accuracy being rounded in the API, data is not exactly as it appears\n"
                 "(i.e., data in the 99% bin include values 98.5% - 99.5%)"
        )

    await ctx.send(embed=embed, file=file)

    os.remove(file_name)

def missing_info():
    return Embed(
        title="Missing Information",
        description="Account has no registered accuracies above 0%",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Histogram(bot))
