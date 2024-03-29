from discord import Embed
from discord.ext import commands
import utils
import errors
from commands.advanced.races import add_stats
from database.bot_users import get_user
import database.users as users
import database.races as races

types = ["races", "time"]
info = {
    "name": "session",
    "aliases": ["ss"],
    "description": "Displays the maximum duration/race get_count sessions for a user with a given minimum break\n"
                   "A session ends whenever two races are greater apart in time than the minimum break",
    "parameters": "[username] <type> <seconds>",
    "defaults": {
        "type": "races",
        "seconds": "1800 (30 minutes)",
    },
    "usages": [
        "session keegant",
        "session keegant races 3600",
        "session keegant time 1d",
    ],
    "import": True,
}


class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def session(self, ctx, *params):
        user = get_user(ctx)
        seconds = 1800
        kind = "races"

        username = user["username"]

        if params and params[0].lower() != "me":
            username = params[0].lower()

        if len(params) > 1:
            kind = utils.get_category(types, params[1])
            if not kind:
                return await ctx.send(embed=errors.invalid_option("type", types))

        if len(params) > 2:
            try:
                seconds = utils.parse_duration_string(params[2])
            except ValueError:
                return await ctx.send(embed=errors.invalid_duration_format())

        if not username:
            return await ctx.send(embed=errors.missing_param(info))

        await run(ctx, user, username, kind, seconds)


async def run(ctx, user, username, kind, seconds):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))
    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = await races.get_races(username, columns=columns)
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
              f"({utils.format_duration_short(seconds, False)} interval)",
        color=user["colors"]["embed"],
    )

    if kind == "time":
        embed.description = utils.format_duration_short(end_time - start_time, False)

    utils.add_profile(embed, stats)
    add_stats(embed, username, session_races, start_time, end_time)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Session(bot))
