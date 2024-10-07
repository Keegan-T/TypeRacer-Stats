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
from utils import errors, colors, urls, strings, embeds
from utils.logging import log
from utils.stats import calculate_points, calculate_seconds

command = {
    "name": "download",
    "aliases": ["getdata", "import", "dl", "gd", "i"],
    "description": "Downloads a given user's complete race history\n"
                   "May take several minutes\n"
                   "Capped at 10,000 races for non-admins",
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
    invoked = True if ctx else False

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

    user = users.get_user(username, universe)
    races_left = stats["races"]
    start_time = 0

    if user:
        log(f"Updating data for {username} (Universe: {universe})")
        new_user = False
        stats["joined"] = user["joined"]
        stats["wpm_best"] = user["wpm_best"]
        stats["retroactive_points"] = user["points_retroactive"]
        stats["seconds"] = user["seconds"]
        stats["characters"] = user["characters"]
        stats["last_updated"] = user["last_updated"]
        start_time = user["last_updated"] - 60 * 15
        races_left -= user["races"]
        if stats["disqualified"]:
            text_results.delete_user_results(username)
            races_300.delete_user_scores(username)

    else:
        log(f"Importing new data for {username} (Universe: {universe})")
        new_user = True
        play_user = users.get_user(username, "play")
        if play_user:
            joined = play_user["joined"]
        else:
            joined = await get_joined(username)
        if not joined:
            if invoked:
                await ctx.send(embed=errors.invalid_username())
            return
        stats["joined"] = joined
        stats["retroactive_points"] = 0
        stats["seconds"] = 0
        stats["characters"] = 0

    new_races = races_left > 0
    if new_races:
        if invoked:
            embed = Embed(
                title=f"Import Request",
                description=f"Downloading {races_left:,} new races for {strings.escape_discord_format(username)}",
                color=bot_user["colors"]["embed"],
            )
            embeds.add_universe(embed, universe)
            await ctx.send(embed=embed)
        log(f"Downloading {races_left:,} new races for {username}")

    text_list = texts.get_texts(as_dictionary=True, universe=universe)
    end_time = time.time()
    race_list = []

    while True:
        if races_left == 0:
            break

        race_data = await get_races(username, start_time, end_time, 1000, universe=universe)

        if race_data == -1:  # Request failed
            raise ValueError

        elif not race_data:  # No more races to download
            break

        for race in race_data:
            # Excluding 0 WPM (modified cheated) races
            wpm = race["wpm"]
            if wpm == 0.0 and universe == "play":
                modified_races.add_cheated_race(username, race)
                continue

            # Checking for new texts
            text_id = race["tid"]
            if text_id not in text_list:
                log(f"New text found! #{text_id}")

                text = {
                    "id": text_id,
                    "quote": get_quote(text_id),
                    "disabled": 0,
                    "ghost": urls.ghost(username, race["gn"], universe)
                }
                texts.add_text(text, universe)
                text_list[text_id] = text

                if universe == "play":
                    await text_results.update_results(text_id)
                    await asyncio.sleep(2)

            quote = text_list[text_id]["quote"]

            # Checking for no accuracy
            if "ac" not in race:
                race["ac"] = 0

            # Checking for 0 points
            if race["pts"] == 0:
                points = calculate_points(quote, race["wpm"])
                race["pts"] = points
                stats["retroactive_points"] += points

            # Manually checking for new best WPM
            if wpm > stats["wpm_best"]:
                stats["wpm_best"] = wpm

            # Only updating seconds / characters for new races
            if not new_user and race["t"] > stats["last_updated"]:
                stats["seconds"] += calculate_seconds(quote, wpm)
                stats["characters"] += len(quote)

            race_list.append((
                strings.race_id(username, race["gn"]), username, race["tid"], race["gn"],
                race["wpm"], race["ac"], race["pts"], race["r"], race["np"], race["t"],
            ))

        end_time = min(race_list, key=lambda r: r[9])[9] - 0.01

    if new_user:
        users.add_user(username, universe)
        if universe == "play":
            await update_award_count(username)

    users.update_stats(stats, universe)

    if new_races:
        races.add_races(race_list, universe)
        users.update_text_stats(username, universe)

    if invoked:
        if new_races:
            await import_complete(ctx, bot_user, username, races_left > 1000, universe)
        else:
            await no_new_races(ctx, bot_user, username, universe)

    log(f"Finished importing {username}")


async def update_award_count(username):
    log("Updating award count")

    awards = await competition_results.get_awards(username)
    first = second = third = 0
    for kind in list(awards.values())[:-1]:
        first += kind["first"]
        second += kind["second"]
        third += kind["third"]
    users.update_awards(username, first, second, third)


async def no_new_races(ctx, user, username, universe):
    username = strings.escape_discord_format(username)
    embed = Embed(
        title=f"Import Request",
        description=f"No new races to import for {username}",
        color=user["colors"]["embed"],
    )
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


async def import_complete(ctx, user, username, notify, universe):
    ping = f"<@{ctx.author.id}>"
    username = strings.escape_discord_format(username)
    embed = Embed(
        title=f"Import Complete",
        description=f"Finished importing new races for {username}",
        color=user["colors"]["embed"],
    )
    embeds.add_universe(embed, universe)

    await ctx.send(
        content=ping if notify else "",
        embed=embed
    )


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
