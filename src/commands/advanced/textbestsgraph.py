import math

from discord.ext import commands

import database.main.races as races
import database.main.texts as texts
import database.main.users as users
from database.bot.users import get_user
from graphs import text_bests_graph
from utils import errors, strings
from utils.embeds import Page, Message, is_embed

categories = ["races", "time", "texts"]
command = {
    "name": "textbestsgraph",
    "aliases": ["tbg"],
    "description": "Displays a graph of a user's text best average over time",
    "parameters": "[username] <category>",
    "defaults": {
        "category": "races"
    },
    "usages": [
        "textbestsgraph keegant time",
        "textbestsgraph keegant races",
        "textbestsgraph keegant texts",
    ],
}


class TextBestsGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textbestsgraph(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
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

    columns = ["number", "wpm", "text_id", "timestamp"]
    race_list = await races.get_races(
        username, columns=columns, universe=universe,
        start_date=user["start_date"], end_date=user["end_date"]
    )
    if not race_list:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)
    race_list.sort(key=lambda r: r[0])

    race_counts = []
    timestamps = []
    changes = []
    averages = []

    text_ids = {}
    disabled_text_ids = texts.get_disabled_text_ids()
    wpm_total = 0
    wpm_count = 0

    for race in race_list:
        if race[2] in disabled_text_ids:
            continue

        race_num = race[0]
        wpm = race[1]
        text_id = race[2]
        timestamp = race[3]

        if text_ids.get(text_id, False):
            if wpm > text_ids[text_id]:
                improvement = wpm - text_ids[text_id]
                wpm_total += improvement
                text_ids[text_id] = wpm
                changes.append(len(changes))
                timestamps.append(timestamp)
                race_counts.append(race_num)
                averages.append(wpm_total / wpm_count)
        else:
            wpm_total += wpm
            wpm_count += 1
            text_ids[text_id] = wpm
            changes.append(len(changes))
            timestamps.append(timestamp)
            race_counts.append(race_num)
            averages.append(wpm_total / wpm_count)

    average = averages[-1]
    texts_typed = len(text_ids)
    next_milestone = 5 * math.ceil(average / 5)
    required_wpm_gain = texts_typed * next_milestone - wpm_total

    description = (
        f"**Text Best Average:** {average:,.2f} WPM\n"
        f"**Texts Typed:** {texts_typed:,}\n"
        f"**Text WPM Total:** {wpm_total:,.0f} WPM\n"
        f"**Gain Until {next_milestone} Average:** {required_wpm_gain:,.0f} WPM"
    )

    x_axes = {
        "races": race_counts,
        "time": timestamps,
        "texts": changes,
    }

    def render(category):
        return lambda: text_bests_graph.render(user, username, x_axes[category], averages, category, universe)

    title = "Text Best Progression"
    pages = [
        Page(
            title=title + " (Over Races)",
            description=description,
            render=render("races"),
            button_name="Over Races",
            default=category == "races",
        ),
        Page(
            title=title + " (Over Time)",
            description=description,
            render=render("time"),
            button_name="Over Time",
            default=category == "time",
        ),
        Page(
            title=title + " (Over Text Changes)",
            description=description + f"\n**Total Text Improvements:** {len(changes):,}",
            render=render("texts"),
            button_name="Over Text Changes",
            default=category == "texts",
        )
    ]

    message = Message(
        ctx, user, pages,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(TextBestsGraph(bot))
