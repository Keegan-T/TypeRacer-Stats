from discord import Embed
from discord.ext import commands

import database.main.races as races
import database.bot.recent_text_ids as recent
import database.main.text_results as top_tens
import database.main.texts as texts
import database.main.users as users
from api.users import get_stats
from commands.account.download import run as download
from config import prefix
from database.bot.users import get_user
from graphs import improvement_graph
from utils import errors, colors, urls, strings, embeds
from utils.embeds import Message, Page
from utils.stats import calculate_performance, calculate_text_performances

command = {
    "name": "text",
    "aliases": ["t", "textgraph", "tg", "personalbest", "pb"],
    "description": "Displays a user's stats about a specific text\n"
                   f"`{prefix}text [username] ^` will use the most recent globally used text id\n"
                   f"`{prefix}textgraph` will add an improvement graph",
    "parameters": "[username] <text_id>",
    "defaults": {
        "text_id": "the text ID of the user's most recent race",
    },
    "usages": ["text keegant 3810446"],
}


class Text(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def text(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command, ctx.channel.id)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, text_id = result
        if text_id == -1:
            text_id = None
        await run(ctx, user, username, text_id)


def get_args(user, args, info, channel_id):
    # Shorthand (-text ^)
    if len(args) == 1 and args[0] == "^" and user["username"]:
        return user["username"], recent.get_recent(channel_id)

    params = "username text_id:-1"

    return strings.parse_command(user, params, args, info, channel_id)


async def run(ctx, user, username, text_id=None, race_number=None):
    universe = user["universe"]
    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    api_stats = get_stats(username, universe=universe)
    await download(stats=api_stats, universe=universe)
    if era_string:
        api_stats = await users.time_travel_stats(api_stats, user)

    graph = ctx.invoked_with in ["textgraph", "tg", "racetextgraph", "rtg"]

    if text_id is None:
        if race_number is None:
            race_number = api_stats["races"]

        if race_number < 1:
            race_number = api_stats["races"] + race_number

        race = races.get_race(username, race_number, universe)

        if not race:
            return await ctx.send(embed=errors.race_not_found(username, race_number, universe))

        text_id = race["text_id"]

    text = texts.get_text(text_id, universe)
    if not text:
        return await ctx.send(embed=errors.unknown_text(universe))
    disabled_texts = texts.get_disabled_text_ids()
    disabled = int(text_id) in disabled_texts

    title = "Text History"
    if ctx.invoked_with in ["racetext", "rt", "racetextgraph", "rtg"]:
        title += f" (Race #{race_number:,})"

    color = user["colors"]["embed"]
    text_description = strings.text_description(dict(text), universe)
    race_list = races.get_text_races(
        username, text_id, universe, start_date=user["start_date"], end_date=user["end_date"]
    )
    if not race_list:
        description = (
            f"{text_description}\n\nUser has no races on this text\n"
            f"[Race this text]({text['ghost']})"
        )
        message = Message(
            ctx, user, Page(description=description),
            title,
            url=urls.trdata_text_races(username, text_id, universe),
            color=color,
            profile=db_stats,
            universe=universe
        )
        await message.send()
        recent.update_recent(ctx.channel.id, text_id)
        return

    times_typed = len(race_list)
    recent_race = race_list[-1]
    stats_string = f"**Times Typed:** {times_typed:,}\n"
    score_display = ""
    average = 0
    best = {}
    previous_best = {}
    worst = {}
    for race in race_list:
        wpm = race["wpm"]
        average += wpm
        if wpm > best.get("wpm", 0):
            best = dict(race)
            if race != race_list[-1]:
                previous_best = dict(race)
        if wpm < worst.get("wpm", float("inf")):
            worst = dict(race)
    average /= times_typed

    if times_typed > 1:
        if recent_race["wpm"] > previous_best["wpm"]:
            score_display = (
                f"**Recent Personal Best!** {recent_race['wpm']:,.2f} WPM (+"
                f"{recent_race['wpm'] - previous_best['wpm']:,.2f} WPM)"
            )
            if not disabled:
                rank, percentile, performance = get_performance_stats(
                    username, universe, text_id, recent_race["wpm"], text["difficulty"]
                )
                score_display += f"\n{get_score_string(rank, percentile, performance)}"

            color = colors.success
            stats_string += get_stats_string(username, universe, average, previous_best, worst, recent_race, previous=True)
        else:
            stats_string += get_stats_string(username, universe, average, best, worst, recent_race, previous=False)

    else:
        color = colors.success
        score_display = f"**New Text!** +{recent_race['wpm']:,.2f} WPM"
        if not disabled:
            rank, percentile, performance = get_performance_stats(
                username, universe, text_id, recent_race["wpm"], text["difficulty"]
            )
            score_display += f"\n{get_score_string(rank, percentile, performance)}"

        stats_string += (
            f"**Recent:** [{recent_race['wpm']:,.2f} WPM]"
            f"({urls.replay(username, recent_race['number'], universe)}) - "
            f"{strings.discord_timestamp(recent_race['timestamp'])}"
        )

    description = f"{score_display}\n\n{text_description}\n\n{stats_string}"
    page = Page(description=description)
    if graph:
        title = f"WPM Improvement - {username} - Text #{text_id}"
        wpm = [race["wpm"] for race in race_list]
        page.render = lambda: improvement_graph.render(user, wpm, title, universe=universe)

    message = Message(
        ctx, user, page, title,
        url=urls.trdata_text_races(username, text_id, universe),
        color=color,
        profile=db_stats,
        universe=universe
    )

    await message.send()

    recent.update_recent(ctx.channel.id, text_id)

    if universe == "play" and not user["end_date"]:
        await top_10_display(ctx, username, text_id, recent_race)


def get_performance_stats(username, universe, text_id, wpm, difficulty):
    text_bests = users.get_text_bests(username, universe=universe)
    calculate_text_performances(text_bests, universe)
    text_bests.sort(key=lambda x: x["performance"], reverse=True)
    text_ids = [t["text_id"] for t in text_bests]
    rank = text_ids.index(int(text_id)) + 1
    percentile = rank / len(text_ids)
    performance = calculate_performance(wpm, difficulty)

    return rank, percentile, performance


def get_score_string(rank, percentile, performance):
    return (
        f":small_blue_diamond: {performance:,.0f} Score "
        f"[(?)](https://discord.com/channels/175964903033667585/746460695670816798 "
        f"\"Score is a measure of performance on a quote, based on difficulty and WPM.\n"
        f"Run -textperformances to see your best quotes!\") - "
        f"Your #{rank:,} (Top {percentile:.2%})"
    )


def get_stats_string(username, universe, average, best, worst, recent_race, previous=True):
    return (
        f"**Average:** {average:,.2f} WPM\n"
        f"**{'Previous ' * previous}Best:** [{best['wpm']:,.2f} WPM]"
        f"({urls.replay(username, best['number'], universe)}) - "
        f"{strings.discord_timestamp(best['timestamp'])}\n"
        f"**Worst:** [{worst['wpm']:,.2f} WPM]"
        f"({urls.replay(username, worst['number'], universe)}) - "
        f"{strings.discord_timestamp(worst['timestamp'])}\n"
        f"**Recent:** [{recent_race['wpm']:,.2f} WPM]"
        f"({urls.replay(username, recent_race['number'], universe)}) - "
        f"{strings.discord_timestamp(recent_race['timestamp'])}"
    )


async def top_10_display(ctx, username, text_id, recent_race):
    top_10 = top_tens.get_top_n(text_id)
    existing_score = next((score for score in top_10 if score["username"] == username), None)
    original_rank = None
    if existing_score:
        original_rank = top_10.index(existing_score) + 1
    await top_tens.update_results(text_id)
    top_10 = top_tens.get_top_n(text_id, 11)
    top_10_score = next((
        score for score in top_10[:10]
        if score["username"] == recent_race["username"] and score["number"] == recent_race["number"]
    ), None)

    if not top_10_score:
        return

    if existing_score:
        top_10 = top_10[:10]

    description = ""
    title = ""
    for i, race in enumerate(top_10):
        style = ""
        increase = ""
        if race["username"] == recent_race["username"] and race["number"] == recent_race["number"]:
            style = "**"
            if original_rank is not None and original_rank > i + 1:
                increase = f"<:increase:1372466536693891142> {original_rank - (i + 1)}"

            if i == 0:
                title = "Top Score! :trophy:"
            else:
                title = f"Top {i + 1} Score! :tada:"
        if i > 9:
            style = "~~"
        user = race["username"]
        accuracy_string = ""
        if race["accuracy"]:
            accuracy_string = f" ({race['accuracy']:.0%})"
        description += (
            f"{strings.rank(i + 1)} {style}{strings.escape_formatting(user)} - [{race['wpm']:,.2f} WPM]"
            f"({urls.replay(user, race['number'])}){accuracy_string}{style} - "
            f"{strings.discord_timestamp(race['timestamp'])} {increase}\n"
        )

    embed = Embed(
        title=title,
        description=description,
        color=colors.success,
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Text(bot))
