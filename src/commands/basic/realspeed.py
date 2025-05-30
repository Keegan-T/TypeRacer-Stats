from discord import Embed, File
from discord.ext import commands

import commands.recent as recent
import database.main.modified_races as modified_races
import database.main.races as races
import database.main.users as users
from api.races import get_race
from api.users import get_stats
from commands.account.download import run as download
from config import prefix
from database.bot.users import get_user
from graphs import match_graph
from graphs.core import remove_file
from utils import errors, colors, urls, strings, embeds

graph_commands = ["realspeedgraph", "rsg", "rg", "adjustedgraph", "ag", "ag*"]
command = {
    "name": "realspeed",
    "aliases": ["rs"] + graph_commands,
    "description": "Displays unlagged and adjusted speeds for a user's race\n"
                   f"`{prefix}realspeed [username] <-n>` will return real speeds for n races ago\n"
                   f"`{prefix}realspeedgraph` will add a graph of the race",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number"
    },
    "usages": [
        "realspeed keegant 100000",
        "realspeed keegant -1",
        "realspeed https://data.typeracer.com/pit/result?id=|tr:keegant|1000000",
    ],
}


class RealSpeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def realspeed(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, ctx.invoked_with in graph_commands, universe)


def get_args(user, args, info):
    params = "username int:0"
    universe = user["universe"]

    result = strings.parse_command(user, params, args, info)
    if embeds.is_embed(result):
        return result

    username, race_number = result

    # Checking for link
    race_info = urls.get_url_info(username)
    if race_info:
        username, race_number, universe = race_info

    # Shorthand (-realspeed -1)
    if user["username"] and username.startswith("-"):
        try:
            race_number = strings.parse_value_string(username)
            username = user["username"]
        except ValueError:
            pass

    return username, race_number, universe


async def run(ctx, user, username, race_number, graph, universe, raw=False):
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    if race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race(username, race_number, universe=universe)
    if not race_info:
        return await ctx.send(embed=errors.race_not_found(username, race_number, universe))

    title = f"{'Raw' if raw else 'Real'} speeds"
    color = user["colors"]["embed"]
    lagged = race_info["lagged"]
    description = strings.text_description(race_info)

    reverse_lag = False
    if "unlagged" not in race_info:
        speeds_string = (
            f"**Lagged:** {lagged:,.2f} WPM\n\n"
            f"{title} not available for this race\n\n"
            f"Completed {strings.discord_timestamp(race_info['timestamp'])}"
        )

    else:
        unlagged = race_info["unlagged"]
        adjusted = race_info["adjusted"]

        if lagged > round(unlagged, 2):
            reverse_lag = True
            description = "\U0001F6A9 Reverse Lagged Score \U0001F6A9\n\n" + description
            color = colors.error

        speeds_string = strings.real_speed_description(race_info)
        if raw:
            speeds_string += strings.raw_speed_description(race_info)
        speeds_string += "Completed " + strings.discord_timestamp(race_info["timestamp"])

    embed = Embed(
        title=f"{title.title()} - Race #{race_number:,}",
        description=description,
        url=urls.replay(username, race_number, universe, stats["disqualified"]),
        color=color
    )

    if race_info.get("distributed", None):
        embed.set_footer(text="Adjusted speed recalculated to account for lag at the start of the race")

    embeds.add_profile(embed, stats)
    embeds.add_universe(embed, universe)

    embed.description += f"\n\n{speeds_string}"

    title = f"Race Graph - {username} - Race #{race_number:,}"

    if graph:
        ranking = {"username": username}

        if raw:
            if ctx.invoked_with in ["rawadjustedgraph", "rag"]:
                y_label = "Raw Adjusted WPM"
                ranking["keystroke_wpm"] = race_info["keystroke_wpm_raw_adjusted"]

            else:
                y_label = "Raw WPM"
                ranking["keystroke_wpm"] = race_info["keystroke_wpm_raw"]

        elif ctx.invoked_with in ["adjustedgraph", "ag", "ag*"]:
            y_label = "Adjusted WPM"
            ranking["keystroke_wpm"] = race_info["keystroke_wpm_adjusted"]

        else:
            y_label = "WPM"
            ranking["keystroke_wpm"] = race_info["keystroke_wpm"]

        file_name = match_graph.render(
            user, [ranking], title, y_label, universe,
            limit_y="*" not in ctx.invoked_with
        )

        embed.set_image(url=f"attachment://{file_name}")
        file = File(file_name, filename=file_name)

        await ctx.send(embed=embed, file=file)

        remove_file(file_name)

    else:
        await ctx.send(embed=embed)

    recent.text_id = race_info["text_id"]

    if universe == "play" and reverse_lag:
        user = users.get_user(username)
        if not user or username == "slowtexts":
            return
        modified_race = modified_races.get_race(universe, username, race_number)
        if not modified_race:
            await download(stats=stats)
            await races.correct_race(universe, username, race_number, race_info)
            embed = Embed(
                title="Reverse Lag Detected",
                description="This score has been corrected in the database",
                color=colors.error,
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RealSpeed(bot))
