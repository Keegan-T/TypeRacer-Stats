from discord import Embed
from discord.ext import commands
import utils
import errors
import urls
import commands.recent as recents
import database.races as races
import database.texts as texts
from database.bot_users import get_user
from commands.basic.realspeed import get_args
from api.users import get_stats
from api.races import get_race_info
from config import prefix

command = {
    "name": "race",
    "aliases": ["r"],
    "description": "Displays information about a user's race\n"
                   f"`{prefix}race [username] <-n>` will return real speeds for n races ago",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number"
    },
    "usages": [
        "race keegant 100000",
        "race keegant -1",
        "race https://data.typeracer.com/pit/result?id=|tr:keegant|1000000",
    ],
    "multiverse": True,
}


class Race(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def race(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, universe)


async def run(ctx, user, username, race_number, universe):
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    if race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race_info(username, race_number, universe=universe)

    if not race_info:
        if universe == "play":
            race_info = races.get_race(username, race_number)
        if not race_info:
            return await ctx.send(embed=errors.race_not_found(username, race_number, universe))
        race_info = dict(race_info)
        quote = texts.get_text(race_info["text_id"])["quote"]
        race_info["quote"] = quote
        race_info["lagged"] = race_info["wpm"]

    embed = Embed(
        title=f"Race #{race_number:,}",
        url=urls.replay(username, race_number, universe),
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats)
    utils.add_universe(embed, universe)

    add_stats(embed, race_info)

    await ctx.send(embed=embed)

    recents.text_id = race_info["text_id"]


def add_stats(embed, race_info):
    embed.description = utils.text_description(race_info)

    rank = race_info["rank"]
    racers = race_info["racers"]
    outcome = "Loss"
    if rank == 1:
        outcome = "Practice" if racers == 1 else "Win"

    if "lagged" not in race_info:
        lagged = race_info["wpm"]
    else:
        lagged = race_info["lagged"]
    seconds = len(race_info["quote"]) * 12 / lagged
    accuracy_string = ""
    if race_info["accuracy"] != 0:
        accuracy_string = f" ({race_info['accuracy'] * 100:,.1f}% Accuracy)"
    stats_string = (
        f"**Speed:** {lagged} WPM{accuracy_string}\n"
        f"**Points:** {race_info['points']:,.2f}\n"
        f"**Race Time:** {utils.format_duration_short(seconds, False)}\n"
        f"**Outcome:** {outcome} ({rank}/{racers})\n\n"
        f"Completed <t:{int(race_info['timestamp'])}:R>"
    )

    embed.add_field(name="Stats", value=stats_string, inline=False)


async def setup(bot):
    await bot.add_cog(Race(bot))
