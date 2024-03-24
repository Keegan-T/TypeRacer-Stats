from datetime import datetime, timezone

from discord import Embed
from discord.ext import commands
import colors
import time
import errors
import database.users as users
import database.races as races
import database.texts as texts
import database.modified_races as modified_races
import database.competition_results as competition_results
import urls
import utils
import asyncio
from database.bot_users import get_user
from api.users import get_stats, get_joined
from api.texts import get_quote
from api.races import get_races
from commands.basic.stats import get_params
from config import bot_admins
import database.text_results as top_tens

info = {
    "name": "download",
    "aliases": ["getdata", "import", "dl", "gd", "i"],
    "description": "Downloads a given user's complete race history\n"
                   "May take several minutes\n"
                   "Capped at 10,000 races for non-admins",
    "parameters": "[username]",
    "usages": ["download keegant"],
    "import": False,
}

import_lock = asyncio.Lock()


class Download(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def download(self, ctx, *params):
        if import_lock.locked():
            return await ctx.send(embed=import_in_progress())

        user = get_user(ctx)

        try:
            username = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await download(username, ctx=ctx, bot_user=user)
        # await run(username=username, ctx=ctx, bot_user=user)

async def download(username=None, stats=None, ctx=None, bot_user=None, override=False):
    invoked = True if ctx else False

    if not stats:
        stats = get_stats(username)
        if not stats:
            if invoked:
                await ctx.send(embed=errors.invalid_username())
            return False
    else:
        username = stats["username"]

    if stats["races"] == 0:
        if invoked:
            await ctx.send(embed=errors.no_races())
        return False

    # Check if the user already imported
    user = users.get_user(username)
    new_user = False if user else True

    races_left = stats["races"]
    start_time = 0
    retroactive_points = 0
    seconds = 0
    characters = 0
    earliest_new_timestamp = datetime.now(timezone.utc).timestamp()

    # Importing new user
    if new_user:
        print(f"Importing new data for {username}")
        joined = await get_joined(username)
        if not joined:
            if invoked:
                await ctx.send(embed=errors.invalid_username())
            return
        stats["joined"] = joined
        print(f"Joined found from profile: {stats['joined']}")

    # Updating existing user
    else:
        print(f"Updating data for {username}")
        stats["joined"] = user["joined"]
        stats["wpm_best"] = user["wpm_best"]
        races_left -= user["races"]
        start_time = user["last_updated"] - 60 * 15
        retroactive_points = user["points_retroactive"]
        seconds = user["seconds"]
        characters = user["characters"]

    print(races_left)
    if races_left > 10_000 and ctx.author.id not in bot_admins and not override:
        if invoked:
            await too_many_races(ctx, bot_user, username, races_left)
        return False

    new_races = races_left > 0

    # Downloading all races
    if new_races:
        if invoked:
            await ctx.send(embed=Embed(
                title=f"Import Request",
                description=f"Downloading {races_left:,} new races for {username}",
                color=bot_user["colors"]["embed"],
            ))

        print(f"Downloading {races_left:,} new races for {username}")

    text_list = texts.get_texts(as_dictionary=True)
    end_time = time.time()
    start = time.time() # For duration logging

    try:
        while True:
            if not new_races:
                break

            race_data = await get_races(username, start_time, end_time, 1000)

            if race_data == -1:  # Request failed
                raise ValueError

            elif not race_data:  # No more races to download
                break

            race_list = []

            for race in race_data:
                # Excluding 0 WPM (modified cheated) races
                wpm = race["wpm"]
                if wpm == 0.0:
                    modified_races.add_cheated_race(username, race)
                    continue

                # Checking for new texts
                text_id = race["tid"]
                if text_id not in text_list:
                    print(f"New text found! #{text_id}")

                    text = {
                        "id": text_id,
                        "quote": get_quote(text_id),
                        "disabled": 0,
                        "ghost": urls.ghost(username, race["gn"])
                    }
                    texts.add_text(text)
                    text_list[text_id] = text

                    await top_tens.update_results(text_id)
                    time.sleep(2)

                quote = text_list[text_id]["quote"]

                # Checking for no accuracy
                if "ac" not in race:
                    race["ac"] = 0

                # Checking for 0 points
                if race["pts"] == 0:
                    points = utils.calculate_points(quote, race["wpm"])
                    race["pts"] = points
                    retroactive_points += points

                # Manually checking for new best WPM
                if wpm > stats["wpm_best"]:
                    stats["wpm_best"] = wpm

                # Only updating seconds / characters for new races
                if not new_user and race["t"] > user["last_updated"]:
                    seconds += utils.calculate_seconds(quote, wpm)
                    characters += len(quote)

                if race["t"] < earliest_new_timestamp:
                    earliest_new_timestamp = race["t"]

                race_list.append(race)
            races.add_races(username, race_list)

            # races_left -= len(race_list)
            end_time = min(race_list, key=lambda r: r["t"])["t"] - 0.01

    except Exception as e:
        races.delete_races_after_timestamp(username, earliest_new_timestamp)
        if invoked:
            await ctx.send(embed=unexpected_error())
        raise e

    print(f"Took {time.time() - start:,.2f}s")

    if not new_races:
        if invoked:
            await no_new_races(ctx, bot_user, username)
        print(f"No new races to import for {username}")

    else:
        if invoked:
            await import_complete(ctx, bot_user, username)
            update_text_stats(username)

    stats["points_retroactive"] = retroactive_points
    stats["seconds"] = seconds
    stats["characters"] = characters

    if new_user:
        users.add_user(stats)
        update_award_count(username)

    else:
        users.update_stats(stats)

    print(f"Finished importing {username}")

    return new_races


def update_text_stats(username):
    print("Updating text stats")

    text_bests = users.get_text_bests(username)
    max_quote = users.get_max_quote(username)
    text_stats = utils.get_text_stats(text_bests)
    text_stats['max_quote_times'] = max_quote['occurrences']
    text_stats['max_quote_id'] = max_quote['text_id']

    users.update_text_stats(username, text_stats)


def update_award_count(username):
    print("Updating award get_count")

    awards = competition_results.get_awards(username)
    first = awards['day']['first'] + awards['week']['first'] + awards['month']['first'] + awards['year']['first']
    second = awards['day']['second'] + awards['week']['second'] + awards['month']['second'] + awards['year']['second']
    third = awards['day']['third'] + awards['week']['third'] + awards['month']['third'] + awards['year']['third']

    users.update_awards(username, first, second, third)

async def no_new_races(ctx, user, username):
    await ctx.send(
        content=f"<@{ctx.author.id}>",
        embed=Embed(
            title=f"Import Request",
            description=f"No new races to import for {username}",
            color=user["colors"]["embed"],
        )
    )


async def too_many_races(ctx, user, username, races_left):
    await ctx.send(
        content=f"<@{ctx.author.id}>",
        embed=Embed(
            title=f"Import Request Rejected",
            description=f"{races_left:,} new races to import for {username}\n"
                        f"Users may only import up to 10,000 races at once\n"
                        f"Have a bot admin run the command",
            color=user["colors"]["embed"],
        )
    )


async def import_complete(ctx, user, username):
    await ctx.send(
        content=f"<@{ctx.author.id}>",
        embed=Embed(
            title=f"Import Complete",
            description=f"Finished importing new races for {username}",
            color=user["colors"]["embed"],
        )
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
        description=f"Something went wrong, stats have not been imported",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Download(bot))
