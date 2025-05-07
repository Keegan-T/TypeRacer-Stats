import asyncio
import time

from discord import Embed
from discord.ext import commands

import database.competition_results as competition_results
import database.modified_races as modified_races
import database.races as races
import database.races_300 as races_300
import database.text_results as text_results
import database.texts as texts
import database.users as users
from api.races import get_races
from api.texts import get_quote
from api.users import get_stats, get_joined
from commands.basic.stats import get_args
from commands.locks import import_lock
from database.bot_users import get_user
from database.texts import update_text_difficulties
from utils import errors, colors, urls, strings, embeds
from utils.logging import log
from utils.stats import calculate_points, calculate_seconds

command = {
    "name": "download",
    "aliases": ["getdata", "import", "dl", "gd", "i"],
    "description": "Downloads a given user's complete race history\n"
                   "May take several minutes",
    "parameters": "[username]",
    "usages": ["download keegant"],
}


class Download(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def download(self, ctx, *args):
        if import_lock.locked():
            return await ctx.send(embed=import_in_progress())

        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        universe = user["universe"]

        async with import_lock:
            await run(username, ctx=ctx, bot_user=user, universe=universe)


async def run(username=None, stats=None, ctx=None, bot_user=None, universe="play"):
    invoked = ctx is not None

    # Getting user stats if not provided
    if not stats:
        stats = get_stats(username, universe=universe)
        if not stats:
            if invoked:
                await ctx.send(embed=errors.invalid_username())
            return
    else:
        username = stats["username"]

    if stats["races"] == 0:
        if invoked:
            await ctx.send(embed=errors.no_races(universe))
        return

    # Checking if user exists, preparing for update
    user, races_left, start_time = get_user_data(username, universe, stats)
    if not user:
        if not await get_new_user_data(username, universe, stats, invoked, ctx):
            return

    new_races = races_left > 0
    if new_races:
        await send_start(ctx, bot_user, username, races_left, universe)

        # Processing races
        race_list, new_texts = await process_races(
            username, universe, start_time, stats, not user
        )

        # Updating database
        if not user:
            users.add_user(username, universe)
            if universe == "play":
                await update_award_count(username)

        races.add_races(race_list, universe)
        users.update_text_stats(username, universe)

    users.update_stats(stats, universe)

    if invoked:
        await send_completion(ctx, bot_user, username, new_races, races_left, universe)

    if new_races:
        log(f"Finished importing {username}")


def get_user_data(username, universe, stats):
    user = users.get_user(username, universe)
    races_left = stats["races"]
    start_time = 0
    if not user:
        return None, races_left, start_time

    log(f"Updating data for {username} (Universe: {universe})")
    stats.update({
        "joined": user["joined"],
        "wpm_best": user["wpm_best"],
        "retroactive_points": user["points_retroactive"],
        "seconds": user["seconds"],
        "characters": user["characters"],
        "last_updated": user["last_updated"],
    })
    start_time = user["last_updated"] - 60 * 15
    races_left -= user["races"]
    if stats["disqualified"]:
        text_results.delete_user_results(username)
        races_300.delete_user_scores(username)

    return user, races_left, start_time


async def get_new_user_data(username, universe, stats, invoked, ctx):
    log(f"Importing new data for {username} (Universe: {universe})")
    play_user = users.get_user(username, "play")
    joined = play_user["joined"] if play_user else await get_joined(username)

    if not joined:
        if invoked:
            await ctx.send(embed=errors.invalid_username())
        return False

    stats.update({
        "joined": joined,
        "retroactive_points": 0,
        "seconds": 0,
        "characters": 0,
    })
    return True


async def process_races(username, universe, start_time, stats, new_user):
    text_list = texts.get_texts(as_dictionary=True, universe=universe)
    new_texts = False
    race_list = []
    end_time = time.time()

    while True:
        race_data = await get_races(username, start_time, end_time, 1000, universe=universe)
        if not race_data:
            break

        for race in race_data:
            # Skipping 0 WPM races
            if race["wpm"] == 0.0 and universe == "play":
                modified_races.add_cheated_race(username, race)
                return None, text_list, False

            # Checking for new texts
            text_id = race["tid"]
            if text_id not in text_list:
                log(f"New text found! #{text_id}")
                text = {
                    "id": text_id,
                    "quote": get_quote(text_id),
                    "disabled": 0,
                    "ghost": urls.ghost(username, text_id, universe),
                    "difficulty": None,
                }
                texts.add_text(text, universe)
                new_texts = True
                text_list[text_id] = text

                if universe == "play":
                    await text_results.update_results(text_id)
                    await asyncio.sleep(2)

            quote = text_list[text_id]["quote"]

            race["ac"] = race.get("ac", 0)
            if race["pts"] == 0:
                points = calculate_points(quote, race["wpm"])
                race["pts"] = points
                stats["retroactive_points"] += points

            # Manually updating best WPM
            if race["wpm"] > stats["wpm_best"]:
                stats["wpm_best"] = race["wpm"]

            # Updating aggregate data
            if not new_user and race["t"] > stats["last_updated"]:
                stats["seconds"] += calculate_seconds(quote, race["wpm"])
                stats["characters"] += len(quote)

            race_list.append((
                strings.race_id(username, race["gn"]), username, text_id, race["gn"],
                race["wpm"], race["ac"], race["pts"], race["r"], race["np"], race["t"]
            ))

        end_time = min(race_list, key=lambda r: r[9])[9] - 0.01

    if new_texts:
        update_text_difficulties(universe=universe)

    return race_list, new_texts


async def update_database(username, universe, stats, race_list, new_texts, new_races, new_user):
    if new_texts:
        update_text_difficulties(universe=universe)

    if new_user:
        users.add_user(username, universe)
        if universe == "play":
            await update_award_count(username)

    users.update_stats(stats, universe)

    if new_races:
        races.add_races(race_list, universe)
        users.update_text_stats(username, universe)


async def send_start(ctx, bot_user, username, races_left, universe):
    if ctx:
        embed = Embed(
            title=f"Import Request",
            description=f"Downloading {races_left:,} new races for "
                        f"{strings.escape_formatting(username)}",
            color=bot_user["colors"]["embed"],
        )
        embeds.add_universe(embed, universe)
        await ctx.send(embed=embed)
    log(f"Downloading {races_left:,} new races for {username}")


async def send_completion(ctx, bot_user, username, new_races, races_left, universe):
    username = strings.escape_formatting(username)
    ping = f"<@{ctx.author.id}>" if races_left > 1000 else ""
    embed = Embed(color=bot_user["colors"]["embed"])

    if new_races:
        embed.title = "Import Complete"
        embed.description = f"Finished importing new races for {username}"
    else:
        embed.title = "Import Request"
        embed.description = f"No new races to import for {username}"

    embeds.add_universe(embed, universe)
    await ctx.send(content=ping, embed=embed)


async def update_award_count(username):
    log("Updating award count")

    awards = await competition_results.get_awards(username)
    first = second = third = 0
    for kind in list(awards.values())[:-1]:
        first += kind["first"]
        second += kind["second"]
        third += kind["third"]
    users.update_awards(username, first, second, third)


def import_in_progress():
    return Embed(
        title=f"Import In Progress",
        description=f"Please wait until the current import has finished",
        color=colors.warning,
    )


def unexpected_error():
    return Embed(
        title=f"Unexpected Error",
        description=f"Something went wrong, races have not been imported",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Download(bot))
