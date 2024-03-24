from discord import Embed
from discord.ext import commands
from src import urls, errors, utils
import commands.recent as recents
import database.races as races
import database.texts as texts
from database.bot_users import get_user
from api.users import get_stats
from api.races import get_race_info

info = {
    "name": "race",
    "aliases": ["r"],
    "description": "Displays information about a specific race",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number"
    },
    "usages": ["race keegant 200000"],
    "import": False,
    "multiverse": True,
}


class Race(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def race(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, race_number, universe = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, race_number, universe)


async def get_params(ctx, user, params):
    username = user["username"]
    race_number = None
    universe = user["universe"]

    if params and params[0].lower() != "me":
        username = params[0]

    # -race -1 shorthand
    if user["username"] and params and params[0].startswith("-"):
        try:
            username = user["username"]
            race_number = utils.parse_value_string(params[0])
        except:
            pass

    if len(params) > 1:
        race_number = params[1]
        try:
            race_number = utils.parse_value_string(race_number)
        except ValueError:
            await ctx.send(embed=errors.invalid_number_format())
            raise

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), race_number, universe


async def run(ctx, user, username, race_number, universe):
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    if race_number is None:
        race_number = stats["races"]

    if race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race_info(username, race_number, universe=universe)

    if not race_info:
        if universe == "play":
            race_info = races.get_race(username, race_number)
        if not race_info:
            return await ctx.send(embed=errors.race_not_found())
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
