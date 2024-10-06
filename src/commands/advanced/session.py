from discord import Embed
from discord.ext import commands

import database.races as races
import database.users as users
from commands.advanced.races import add_stats
from database.bot_users import get_user
from utils import errors, strings, embeds

categories = ["races", "time"]
command = {
    "name": "session",
    "aliases": ["ss"],
    "description": "Displays the maximum duration/race get_count sessions for a user with a given minimum break\n"
                   "A session ends whenever two races are greater apart in time than the minimum break",
    "parameters": "[username] <category> <time>",
    "defaults": {
        "category": "races",
        "time": "30 minutes",
    },
    "usages": [
        "session keegant",
        "session keegant races 1h30m",
        "session keegant time 1h30m",
    ],
}


class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def session(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, category, seconds = result
        await run(ctx, user, username, category, seconds)


def get_args(user, args, info):
    params = f"username category:{'|'.join(categories)} duration:1800"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, kind, seconds):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = await races.get_races(
        username, columns=columns, universe=universe, start_date=user["start_date"], end_date=user["end_date"]
    )
    if not race_list:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)
    race_list.sort(key=lambda x: x[7])
    race_range = [0, 0]
    start_race = 0

    if kind == "races":
        session = 1
        current_session = 1

        for i in range(1, len(race_list)):
            current_timestamp = race_list[i][7]
            previous_timestamp = race_list[i - 1][7]
            time_difference = current_timestamp - previous_timestamp

            if time_difference < seconds:
                current_session += 1
            else:
                if current_session > session:
                    session = current_session
                    race_range = [start_race, i - 1]

                current_session = 1
                start_race = i

        if current_session > session:
            race_range = [start_race, len(race_list) - 1]

    else:
        session = 0
        current_session = 0

        for i in range(1, len(race_list)):
            current_timestamp = race_list[i][7]
            previous_timestamp = race_list[i - 1][7]
            time_difference = current_timestamp - previous_timestamp

            if time_difference < seconds:
                current_session += time_difference
            else:
                if current_session > session:
                    session = current_session
                    race_range = [start_race, i - 1]

                current_session = 0
                start_race = i

        if current_session > session:
            race_range = [start_race, len(race_list) - 1]

    session_races = race_list[race_range[0]:race_range[1] + 1]
    start_time = session_races[0][7]
    end_time = session_races[-1][7]

    embed = Embed(
        title=f"{'Longest' if kind == 'time' else 'Highest Race'} Session "
              f"({strings.format_duration_short(seconds, False)} interval)",
        color=user["colors"]["embed"],
    )

    if kind == "time":
        embed.description = strings.format_duration_short(end_time - start_time, False)

    embeds.add_profile(embed, stats, universe)
    add_stats(embed, username, session_races, start_time, end_time, universe=universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)


async def setup(bot):
    await bot.add_cog(Session(bot))
