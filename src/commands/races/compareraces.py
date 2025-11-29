from discord import Embed
from discord.ext import commands

import database.bot.recent_text_ids as recent
from api.users import get_stats
from commands.account.download import run as download
from config import prefix
from database.bot.users import get_user
from database.main import races
from database.main import users
from database.main.texts import get_text
from graphs import match_graph
from utils import errors, urls, colors, strings
from utils.embeds import Page, Message, is_embed

command = {
    "name": "compareraces",
    "aliases": ["cr"],
    "description": "Displays a single graph of two separate races\n"
                   f"Use `{prefix}compareraces [username] [text_id]` to compare\n"
                   f"your best and most recent race for a given text ID\n"
                   f"Use `{prefix}compareraces [username1] [text_id] [username2]`\n"
                   f"to compare 2 given users best race on a given text ID",
    "parameters": "[username|link] <text_id> [username2|link]",
    "usages": [
        "compareraces me 3810446",
        "compareraces zak389 3550141 arenasnow",
        "compareraces zak389|18533 joshua728|29687",
    ],
    "temporal": False,
}


class CompareRaces(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def compareraces(self, ctx, *args):
        user = get_user(ctx)
        args, user = strings.set_wpm_metric(args, user)

        result = await get_args(user, args, command, user["universe"], ctx.channel.id)
        if is_embed(result):
            return await ctx.send(embed=result)

        if len(result) == 4:
            username, username2, text_id, universe = result
            return await run_text(ctx, user, username, username2, text_id, universe)

        username1, username2, race_number1, race_number2, universe = result
        await run(ctx, user, username1, username2, race_number1, race_number2, universe)


async def get_args(user, args, info, universe, channel_id):
    username = user["username"]
    text_id = None
    username2 = None
    universe = user["universe"]

    if len(args) == 1:
        if args[0] != "me":
            username = args[0]

    if len(args) == 2:
        arg1, arg2 = args

        if "|" in arg1 and "|" in arg2:
            url_info = urls.get_url_info(arg1)
            if url_info:
                username, number, universe = url_info
            else:
                info = arg1.rsplit("|")
                username = info[-2]
                number = info[-1]

            url_info = urls.get_url_info(arg2)
            if url_info:
                username2, number2, _ = url_info
            else:
                info = arg2.rsplit("|")
                username2 = info[-2]
                number2 = info[-1]

            db_stats = users.get_user(username, universe)
            if not db_stats:
                return errors.import_required(username, universe)
            await download(username)

            db_stats = users.get_user(username2, universe)
            if not db_stats:
                return errors.import_required(username2, universe)
            await download(username2)

            return username, username2, int(number), int(number2), universe

        else:
            if arg1 != "me":
                username = arg1
            text_id = arg2

    if len(args) == 3:
        if args[0] != "me":
            username = args[0]
        if args[2] != "me":
            username2 = args[2]
        text_id = args[1]

    db_stats = users.get_user(username, universe)
    if not db_stats:
        return errors.import_required(username, universe)
    await download(username)

    if username2:
        db_stats = users.get_user(username2, universe)
        if not db_stats:
            return errors.import_required(username2, universe)
        await download(username2)

    if text_id == "^":
        text_id = recent.get_recent(channel_id)

    if text_id is None:
        text_id = races.get_latest_text_id(username, universe)

    text = get_text(text_id, user["universe"])
    if not text:
        return errors.unknown_text(universe)

    return username, username2, int(text_id), universe


async def run(ctx, user, username1, username2, race_number1, race_number2, universe, stats=None):
    wpm_metric = user["settings"]["wpm"]

    race_info1 = await races.get_race(username1, race_number1, universe, get_log=True, get_keystrokes=True)
    if not race_info1["log"]:
        return await ctx.send(embed=errors.logs_not_found(username1, race_number1, universe))

    race_info2 = await races.get_race(username2, race_number2, universe, get_log=True, get_keystrokes=True)
    if not race_info2["log"]:
        return await ctx.send(embed=errors.logs_not_found(username2, race_number2, universe))

    if race_info1["text_id"] != race_info2["text_id"]:
        return await ctx.send(embed=Embed(
            title="Mismatched Text IDs",
            description="Race comparison can only be made\non races with the same text ID",
            color=colors.error,
        ))

    text = get_text(race_info1["text_id"], universe=universe)
    if not text:
        return await ctx.send(embed=errors.unknown_text(universe))

    column = {
        "wpm_raw": "raw_adjusted",
        "wpm_pauseless": "pauseless_adjusted",
    }.get(wpm_metric, wpm_metric)
    wpm1 = race_info1[column]
    wpm2 = race_info2[column]

    if not stats and wpm1 < wpm2:
        username1, username2 = username2, username1
        race_number1, race_number2 = race_number2, race_number1
        race_info1, race_info2 = race_info2, race_info1
        wpm1, wpm2 = wpm2, wpm1

    accuracy1 = race_info1["accuracy"]
    accuracy2 = race_info2["accuracy"]
    timestamp1 = race_info1["timestamp"]
    timestamp2 = race_info2["timestamp"]

    description = (
        f"{strings.escape_formatting(username1)} - "
        f"[{wpm1:,.2f} WPM]({urls.replay(username1, race_number1, universe)}) "
        f"({accuracy1:,.2%}) {strings.discord_timestamp(timestamp1)}\nvs.\n"
        f"{strings.escape_formatting(username2)} - "
        f"[{wpm2:,.2f} WPM]({urls.replay(username2, race_number2, universe)}) "
        f"({accuracy2:,.2%}) {strings.discord_timestamp(timestamp2)}\n"
    )

    if stats:
        if stats["type"] == "new":
            description = "**New Best**\n" + description + "**Previous Best**"
            user["colors"]["embed"] = colors.success
        else:
            description = "**Best**\n" + description + "**Recent**"

    description = f"{strings.text_description(dict(text), universe)}\n\n" + description
    rankings = [
        {
            "username": username1,
            "keystroke_wpm": race_info1[("keystroke_" + wpm_metric).replace("_unlagged", "")],
        },
        {
            "username": username2,
            "keystroke_wpm": race_info2[("keystroke_" + wpm_metric).replace("_unlagged", "")],
        }
    ]

    if username1 == username2 == user["username"]:
        rankings[1]["username"] = username2 + "\u200B"

    graph_title = f"{username1} #{race_number1:,} vs. {username2} #{race_number2:,}"
    page = Page(
        title="Race Comparison",
        description=description,
        render=lambda: match_graph.render(user, rankings, graph_title, "WPM", universe),
    )

    profile = None
    if username1 == username2:
        if not stats:
            stats = await get_stats(username1, universe=universe)
        profile = stats

    message = Message(
        ctx, user, page,
        profile=profile,
        universe=universe,
        time_travel=False,
        wpm_metric=wpm_metric,
    )

    await message.send()

    recent.update_recent(ctx.channel.id, race_info1["text_id"])


async def run_text(ctx, user, username, username2, text_id, universe):
    stats = await get_stats(username, universe=universe)
    await download(racer=stats, universe=universe)
    wpm_metric = user["settings"]["wpm"]

    race_list = races.get_text_races(username, text_id, universe, wpm=wpm_metric)

    if username2:
        if not race_list:
            return await ctx.send(embed=no_text_races(username))

        # stats2 = await get_stats(username2, universe=universe)
        # await download(racer=stats2, universe=universe)
        race_list2 = races.get_text_races(username2, text_id, universe, wpm=wpm_metric)
        if not race_list2:
            return await ctx.send(embed=no_text_races(username2))

        best1 = max(race_list, key=lambda r: r["wpm"])
        best2 = max(race_list2, key=lambda r: r["wpm"])

        await run(ctx, user, username, username2, best1["number"], best2["number"], universe)

    else:
        if len(race_list) < 2:
            return await ctx.send(embed=not_enough_races())

        recent_race = race_list[-1]
        best = max(race_list, key=lambda r: r["wpm"])
        previous_best = max(race_list[:-1], key=lambda r: r["wpm"])

        if recent_race["wpm"] > previous_best["wpm"]:
            stats["type"] = "new"
            await run(ctx, user, username, username, recent_race["number"], previous_best["number"], universe, stats)
        else:
            stats["type"] = "old"
            await run(ctx, user, username, username, best["number"], recent_race["number"], universe, stats)


def not_enough_races():
    return Embed(
        title="Not Enough Races",
        description="User must have at least 2 races\non this text to compare by text ID",
        color=colors.error,
    )


def no_text_races(username):
    return Embed(
        title="No Text Races",
        description=f"{strings.escape_formatting(username)} has no races on this text",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(CompareRaces(bot))
