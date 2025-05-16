from discord import Embed, File
from discord.ext import commands

from api import users
from api.races import get_race
from api.users import get_stats
from commands import recent
from commands.account.download import run as download
from config import prefix
from database import races
from database.bot_users import get_user
from database.texts import get_text
from graphs import match_graph
from graphs.core import remove_file
from utils import errors, embeds, urls, colors, strings

command = {
    "name": "compareraces",
    "aliases": ["cr"],
    "description": "Displays a single graph of two separate races\n"
                   f"Use `{prefix}compareraces [username] [text_id]` to compare\n"
                   f"your best and most recent race for a given text ID\n"
                   f"Use `{prefix}compareraces [username1] [text_id] [username2]`\n"
                   f"to compare 2 given users best race on a given text ID",
    "parameters": "[username1|number1/link] [username2|number2/link]",
    "usages": [
        "compareraces keegant|100000 keegant|1003398",
        "compareraces me 3810446",
        "compareraces zak389 3550141 arenasnow",
    ],
    "temporal": False,
}


class CompareRaces(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def compareraces(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        if len(result) == 4:
            username, username2, text_id, universe = result
            return await run_text(ctx, user, username, username2, text_id, universe)

        username1, username2, race_number1, race_number2, universe = result
        await run(ctx, user, username1, username2, race_number1, race_number2, universe)


def get_args(user, args, info):
    try:
        username2 = None
        if len(args) == 0:
            username = user["username"]
            race = users.get_latest_race(username, user["universe"])
            text_id = race["tid"] if race else None

        elif len(args) == 1:
            username = user["username"] if args[0] == "me" else args[0]
            race = users.get_latest_race(username, user["universe"])
            text_id = race["tid"] if race else None

        else:
            username = user["username"] if args[0] == "me" else args[0]
            text_id = args[1]
            if len(args) == 3:
                username2 = user["username"] if args[2] == "me" else args[2]

        if text_id is None:
            raise ValueError

        stats = users.get_stats(username, universe=user["universe"])
        if not stats:
            raise ValueError

        if username2:
            stats = users.get_stats(username2, universe=user["universe"])
            if not stats:
                raise ValueError

        if text_id == "^":
            text_id = recent.text_id

        text = get_text(text_id, user["universe"])
        if not text:
            raise ValueError

        return username, username2, int(text_id), user["universe"]
    except ValueError:
        pass

    # Links
    race_info1 = urls.get_url_info(args[0])
    if race_info1:
        username1, race_number1, universe = race_info1
        race_info2 = urls.get_url_info(args[1])
        if race_info2:
            username2, race_number2, _ = race_info2
            return username1, username2, race_number1, race_number2, universe

    # Strings
    try:
        username1, race_number1 = args[0].split("|")
        username2, race_number2 = args[1].split("|")
        universe = user["universe"]
        return username1, username2, int(race_number1), int(race_number2), universe
    except ValueError:
        return errors.invalid_argument(info)


async def run(ctx, user, username1, username2, race_number1, race_number2, universe, stats=None):
    race_info1 = await get_race(username1, race_number1, universe=universe)
    if not race_info1 or "unlagged" not in race_info1:
        return await ctx.send(embed=errors.logs_not_found(username1, race_number1, universe))

    race_info2 = await get_race(username2, race_number2, universe=universe)
    if not race_info2 or "unlagged" not in race_info2:
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

    unlagged1 = race_info1["unlagged"]
    unlagged2 = race_info2["unlagged"]

    if not stats and unlagged1 < unlagged2:
        username1, username2 = username2, username1
        race_number1, race_number2 = race_number2, race_number1
        race_info1, race_info2 = race_info2, race_info1
        unlagged1, unlagged2 = unlagged2, unlagged1

    accuracy1 = race_info1["accuracy"] * 100
    accuracy2 = race_info2["accuracy"] * 100
    timestamp1 = race_info1["timestamp"]
    timestamp2 = race_info2["timestamp"]

    description = (
        f"{strings.escape_formatting(username1)} - "
        f"[{unlagged1:,.2f} WPM]({urls.replay(username1, race_number1, universe)}) "
        f"({accuracy1:,.1f}%) {strings.discord_timestamp(timestamp1)}\nvs.\n"
        f"{strings.escape_formatting(username2)} - "
        f"[{unlagged2:,.2f} WPM]({urls.replay(username2, race_number2, universe)}) "
        f"({accuracy2:,.1f}%) {strings.discord_timestamp(timestamp2)}\n"
    )

    if stats:
        if stats["type"] == "new":
            description = "**New Best**\n" + description + "**Previous Best**"
            user["colors"]["embed"] = colors.success
        else:
            description = "**Best**\n" + description + "**Recent**"

    description = f"{strings.text_description(dict(text), universe)}\n\n" + description

    embed = Embed(
        title="Race Comparison",
        description=description,
        color=user["colors"]["embed"],
    )
    if username1 == username2:
        if not stats:
            stats = get_stats(username1, universe=universe)
        embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    rankings = [
        {
            "username": username1,
            "average_wpm": race_info1["wpm_over_keystrokes"],
        },
        {
            "username": username2,
            "average_wpm": race_info2["wpm_over_keystrokes"],
        }
    ]

    if username1 == username2 == user["username"]:
        rankings[1]["username"] = username2 + "\u200B"

    title = f"{username1} #{race_number1:,} vs. {username2} #{race_number2:,}"
    file_name = match_graph.render(user, rankings, title, "WPM", universe)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    remove_file(file_name)

    recent.text_id = race_info1["text_id"]


async def run_text(ctx, user, username, username2, text_id, universe):
    stats = get_stats(username, universe=universe)
    await download(stats=stats, universe=universe)

    race_list = races.get_text_races(username, text_id, universe)

    if username2:
        if not race_list:
            return await ctx.send(embed=no_text_races(username))

        stats2 = get_stats(username2, universe=universe)
        await download(stats=stats2, universe=universe)

        race_list2 = races.get_text_races(username2, text_id, universe)
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
