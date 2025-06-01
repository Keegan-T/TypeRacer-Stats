import asyncio
import time

from discord import Embed
from discord.ext import commands

import database.main.club_races as club_races
import database.main.competition_results as competition_results
import database.main.races as races
import database.main.text_results as text_results
import database.main.texts as texts
import database.main.users as users
from api.races import get_races
from api.texts import get_quote
from api.users import get_stats, get_joined
from commands.basic.stats import get_args
from commands.locks import import_lock
from database.bot.users import get_user
from database.main import deleted_races, modified_races
from utils import errors, colors, strings
from utils.embeds import Page, Message, is_embed
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
        if is_embed(result):
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
        if not await get_new_user_data(username, universe, stats):
            if invoked:
                await ctx.send(embed=errors.invalid_username())
            return

    new_races = races_left > 0
    if new_races:
        await send_start(ctx, bot_user, username, races_left, universe)

        # Processing races
        race_list = await process_races(username, universe, start_time, stats, not user)

        # Updating database
        if not user:
            users.create_user(username, stats["joined"], universe)
            if universe == "play":
                await update_award_count(username)

        race_list.sort(key=lambda x: x[9])
        races.add_races(race_list)

    users.update_user(
        username, stats["display_name"], stats["premium"],
        stats["country"], stats["avatar"]
    )
    users.update_stats(
        universe, username, stats["wpm_average"], stats["wpm_best"], stats["wpm_verified"],
        stats["races"], stats["wins"], stats["points"], stats["points_retroactive"],
        stats["seconds"], stats["characters"], stats["disqualified"]
    )

    if new_races:
        users.update_text_stats(username, universe)

    if invoked:
        await send_completion(ctx, bot_user, username, races_left, universe)

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
        "wpm_best": user["wpm_best"],
        "points_retroactive": user["points_retroactive"],
        "seconds": user["seconds"],
        "characters": user["characters"],
        "last_updated": user["last_updated"],
    })
    start_time = user["last_updated"] - 60 * 15
    races_left -= user["races"]
    if stats["disqualified"]:
        text_results.delete_user_results(username)
        club_races.delete_user_scores(username)

    return user, races_left, start_time


async def get_new_user_data(username, universe, stats):
    log(f"Importing new data for {username} (Universe: {universe})")
    play_user = users.get_user(username, "play")
    joined = play_user["joined"] if play_user else await get_joined(username)

    if not joined:
        return False

    stats.update({
        "joined": joined,
        "points_retroactive": 0,
        "seconds": 0,
        "characters": 0,
    })
    return True


async def process_races(username, universe, start_time, stats, new_user):
    text_list = texts.get_texts(as_dictionary=True, universe=universe)
    modified_ids = modified_races.get_ids()
    deleted_ids = deleted_races.get_ids()
    race_list = []
    end_time = time.time()

    while True:
        race_data = await get_races(username, start_time, end_time, 1000, universe=universe)
        if not race_data:
            break

        for race in race_data:
            number = race["gn"]
            race_id = f"{universe}|{username}|{number}"

            # Treating 0 WPM races as deleted
            if race_id in deleted_ids:
                log(f"Skipping deleted race {race_id}")
                continue
            elif race["wpm"] == 0.0:
                log(f"Adding deleted race {race_id}")
                deleted_races.add_race(universe, username, number, race["wpm"])
                continue

            # Restoring modified values
            if race_id in modified_ids:
                modified_race = modified_races.get_race(universe, username, number)
                log(f"Using modified race {race_id}")
                race["wpm"] = modified_race["wpm_modified"]

            # Checking for new texts
            text_id = race["tid"]
            if text_id not in text_list:
                log(f"New {universe} text found! #{text_id}")
                text = {
                    "text_id": text_id,
                    "quote": get_quote(text_id),
                    "ghost_username": username,
                    "ghost_number": number,
                }
                texts.add_text(text, universe)
                text_list[text_id] = text

                if universe == "play":
                    await text_results.update_results(text_id)
                    await asyncio.sleep(2)

            quote = text_list[text_id]["quote"]

            race["ac"] = race.get("ac", 0)
            if race["pts"] == 0:
                points = calculate_points(quote, race["wpm"])
                race["pts"] = points
                stats["points_retroactive"] += points

            # Manually updating best WPM
            if race["wpm"] > stats["wpm_best"]:
                stats["wpm_best"] = race["wpm"]

            # Updating aggregate data
            if not new_user and race["t"] > stats["last_updated"]:
                stats["seconds"] += calculate_seconds(quote, race["wpm"])
                stats["characters"] += len(quote)

            race_list.append((
                universe, username, number, text_id, race["wpm"],
                race["ac"], race["pts"], race["r"], race["np"], race["t"],
                None, None, None, None, None, None, None, None, None, None  # Waiting for logs API
            ))

        end_time = min(race_list, key=lambda r: r[9])[9] - 0.01

    return race_list


async def send_start(ctx, bot_user, username, races_left, universe):
    if ctx:
        message = Message(
            ctx, bot_user, Page(
                title=f"Import Request",
                description=f"Downloading {races_left:,} new races for "
                            f"{strings.escape_formatting(username)}",
            ),
            universe=universe,
            time_travel=False,
        )
        await message.send()
    log(f"Downloading {races_left:,} new races for {username}")


async def send_completion(ctx, bot_user, username, races_left, universe):
    username = strings.escape_formatting(username)
    page = Page()

    if races_left > 0:
        page.title = "Import Complete"
        page.description = f"Finished importing new races for {username}"
    else:
        page.title = "Import Request"
        page.description = f"No new races to import for {username}"

    message = Message(
        ctx, bot_user, page,
        content=f"<@{ctx.author.id}>" if races_left > 1000 else "",
        universe=universe,
        time_travel=False,
    )

    await message.send()


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
