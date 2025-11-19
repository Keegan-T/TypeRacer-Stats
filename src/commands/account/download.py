import asyncio
import zlib

from aiohttp import ClientResponseError
from discord import Embed
from discord.ext import commands

import database.main.club_races as club_races
import database.main.competition_results as competition_results
import database.main.races as races
import database.main.text_results as text_results
import database.main.texts as texts
import database.main.users as users
from api.core import date_to_timestamp
from api.races import get_races, get_universe_multiplier, get_races_historical
from api.texts import get_text
from api.users import get_stats, get_racer, get_joined
from commands.locks import import_lock
from commands.stats.stats import get_args
from database.bot.users import get_user
from database.main import deleted_races, typing_logs
from utils import errors, colors, strings, logs, dates
from utils.embeds import Page, Message, is_embed
from utils.logging import log
from utils.stats import calculate_points, calculate_ms

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


async def run(username=None, racer={}, ctx=None, bot_user=None, universe="play"):
    invoked = ctx is not None
    username = racer.get("username", username)
    user_data = users.get_user_data(username)
    user_stats = users.get_user_stats(username, universe)

    if racer:
        if user_data:
            racer = extract_racer_data(racer)
        else:
            if "total_races" not in racer:
                racer = await get_racer(racer["username"], universe)
            else:
                join_date = await get_joined(username)
                racer["joined_at"] = join_date
    else:
        if user_data:
            racer = extract_racer_data(await get_stats(username, universe=universe))
        else:
            racer = await get_racer(username, universe)
            if not racer:
                return await ctx.send(embed=errors.invalid_username())
            if racer["total_races"] == 0:
                return await ctx.send(embed=errors.no_races(universe))

    start_time = user_data.get("last_updated", 0)
    imported_races = user_stats.get("races", 0)
    if user_stats.get("disqualified", None) and universe == "play":
        text_results.delete_user_results(username)
        club_races.delete_user_scores(username)

    total_races = racer["total_races"]
    races_left = total_races - imported_races
    log(f"**Importing data for {username} (Universe: {universe})**")
    if races_left > 0:
        await send_start(ctx, bot_user, username, races_left, universe)

        recent_races = await get_recent_races(username, universe, start_time)
        if recent_races:
            cutoff = min(recent_races, key=lambda r: r["rn"])["rn"] - 1
            points_retroactive, total_time, characters = await process_races(
                recent_races, universe, username, imported_races, batch_size=1000
            )
        else:
            points_retroactive = total_time = characters = 0
            cutoff = total_races

        try:
            historical_generator = get_historical_races(username, universe, cutoff, imported_races)
            async for historical_chunk in historical_generator:
                chunk_points, chunk_time, chunk_chars = await process_races(
                    historical_chunk, universe, username, imported_races, batch_size=1000
                )
                points_retroactive += chunk_points
                total_time += chunk_time
                characters += chunk_chars
        except ClientResponseError as e:
            if e.status == 429:
                return await ctx.send(embed=rate_limit_exceeded())
            else:
                raise e

    if not user_data:
        users.create_user_data(racer)
    if not user_stats:
        users.create_user_stats(racer)

    users.update_user_data(racer)
    users.update_user_stats(racer)

    if races_left > 0:
        users.update_user_aggregate_stats(username, universe, points_retroactive, total_time, characters)
        users.update_text_stats(username, universe)

    if invoked:
        await send_completion(ctx, bot_user, username, races_left, universe)

    if not user_stats and universe == "play":
        await update_award_count(username)

    if races_left > 0:
        log(f"Finished importing {username}")


def extract_racer_data(stats):
    return dict(
        username=stats["username"],
        name=stats["display_name"],
        country=stats["country"],
        avatar=stats["avatar"],
        premium=stats["premium"],
        universe=stats["universe"],
        total_races=stats["races"],
        total_wins=stats["wins"],
        points=stats["points"],
        avg_wpm=stats["wpm_average"],
        best_wpm=stats["wpm_best"],
        cert_wpm=stats["wpm_verified"],
        dqd=stats["disqualified"],
    )


async def process_races(race_list, universe, username, imported_races, batch_size=1000):
    processor = RaceProcesser(universe)
    points_retroactive = total_time = characters = 0
    race_list = sorted(race_list, key=lambda r: r["t"])
    seen = set(range(1, imported_races + 1))

    for i in range(0, len(race_list), batch_size):
        batch = race_list[i:i + batch_size]
        races_batch = []
        logs_batch = []

        for race_data in batch:
            race = await processor.process_race(universe, username, race_data)
            if not race:
                continue

            number = race["number"]
            if number not in seen:
                seen.add(number)
                characters += race["characters"]
                total_time += race["duration"]
                if race["retroactive"]:
                    points_retroactive += race["points"]

                races_batch.append(race)
                if race["typing_log"]:
                    logs_batch.append(race)

        if races_batch:
            races.add_races(races_batch)
        if logs_batch:
            typing_logs.add_logs(logs_batch)

        del races_batch, logs_batch, batch
        await asyncio.sleep(0.1)

    return points_retroactive, total_time, characters


async def get_recent_races(username, universe, start_time):
    race_list = []
    end_time = dates.now().timestamp()

    while True:
        race_data = await get_races(username, start_time, end_time, 1000, universe=universe)
        if not race_data:
            break

        for i in range(len(race_data)):
            race_data[i]["t"] = date_to_timestamp(race_data[i]["t"])

        race_list += race_data
        end_time = min(race_data, key=lambda r: r["t"])["t"] - 0.0001
        log(f"Fetched races {race_data[-1]['rn']:,} - {race_data[0]['rn']:,}")

    return race_list


async def get_historical_races(username, universe, cutoff, imported_races):
    races_left = cutoff - imported_races
    all_historical_races = []

    if races_left > 0:
        log(f"Downloading {races_left:,} historical races in chunks")
        bucket = cutoff // 1000
        final_bucket = imported_races // 1000

        while bucket >= final_bucket:
            race_list = await get_races_historical(username, universe, bucket)
            all_historical_races.extend(race_list)
            log(f"Fetched races {max(bucket * 1000, 1):,} - {min(bucket * 1000 + 999, cutoff):,}")

            if len(all_historical_races) >= 5000:
                yield all_historical_races
                all_historical_races = []

            bucket -= 1

    if all_historical_races:
        yield all_historical_races


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
    log(f"Downloading {races_left:,} new races")


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


class RaceProcesser:
    def __init__(self, universe):
        self.text_list = texts.get_texts(as_dictionary=True, universe=universe)
        self.deleted_ids = deleted_races.get_ids()

    async def process_race(self, universe, username, race):
        number = race["rn"]
        race_id = f"{universe}|{username}|{number}"
        wpm = race["wpm"]
        typing_log = race["kl"]

        # Handling deleted races (0 WPM)
        if race_id in self.deleted_ids:
            log(f"Skipping deleted race {race_id}")
            return None
        elif wpm == 0.0:
            log(f"Adding deleted race {race_id}")
            deleted_races.add_race(universe, username, number, typing_log)
            return None

        # Checking for new texts
        text_id = race["tid"]
        if text_id not in self.text_list.keys():
            log(f"New {universe} text found! #{text_id}")
            text = await get_text(text_id)
            text["quote"] = text["text"]
            texts.add_text(text, universe)
            self.text_list[text_id] = text
            if universe == "play":
                await text_results.update_results(text_id)

        quote = self.text_list[text_id]["quote"]
        accuracy = race.get("acc", 0)
        points = race["pts"]
        retroactive = False
        if points == 0:
            points = calculate_points(quote, wpm)
            retroactive = True

        # Typing log data
        multiplier = get_universe_multiplier(universe)
        if not typing_log:
            race.update({
                "unlagged": wpm,
                "adjusted": wpm,
                "duration": calculate_ms(quote, wpm)
            })
        else:
            try:
                delay_data, action_data = logs.split_log(typing_log)
            except TypeError:
                typing_log = zlib.decompress(typing_log).decode("utf-8")
                delay_data, action_data = logs.split_log(typing_log)
            if not action_data:
                log_details = logs.get_old_log_stats(delay_data, quote, multiplier)
            else:
                log_details = logs.get_log_stats(delay_data, action_data, multiplier)
            race.update(log_details)

        return dict(
            universe=universe,
            username=username,
            number=number,
            text_id=text_id,
            wpm=wpm,
            accuracy=accuracy,
            points=points,
            characters=len(quote),
            rank=race["r"],
            racers=race["nr"],
            race_id=race["rid"],
            timestamp=race["t"],
            unlagged=race["unlagged"],
            adjusted=race["adjusted"],
            duration=race["duration"],
            raw_adjusted=race.get("raw_adjusted", None),
            pauseless_adjusted=race.get("pauseless_adjusted", None),
            start=race.get("start", None),
            correction_time=race.get("correction_time", None),
            pause_time=race.get("pause_time", None),
            typing_log=typing_log,
            retroactive=retroactive,
        )


def rate_limit_exceeded():
    return Embed(
        title="Rate Limit Exceeded",
        description="The rate limit for historical imports has\n"
                    "been reached, please try again tomorrow",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Download(bot))
