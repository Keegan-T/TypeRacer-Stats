from discord import Embed, File
from discord.ext import commands
import os

import graphs
import utils
import errors
import urls
import colors
from urllib.parse import urlparse
from config import prefix
from database.bot_users import get_user
from api.users import get_stats
from api.races import get_race_info
import commands.recent as recents
import database.races as races
import database.races_300 as races_300
import database.modified_races as modified_races
from commands.basic.download import run as download, update_text_stats

graph_commands = ["realspeedgraph", "rsg", "rg", "adjustedgraph", "ag", "ag*"]
info = {
    "name": "realspeed",
    "aliases": ["rs"] + graph_commands,
    "description": "Displays unlagged and adjusted speeds for a given user's race\n"
                   "Race number defaults to user's latest race\n"
                   f"`{prefix}realspeed [replay_link]` will display the real speeds for a replay link\n"
                   f"`{prefix}realspeed [username] <-n>` will return real speeds for n races ago",
    "parameters": "[username] <race_number>",
    "usages": [
        "realspeed keegant 100000",
        "realspeed keegant -1",
        "realspeed https://data.typeracer.com/pit/result?id=|tr:keegant|1000000",
    ],
    "import": False,
    "multiverse": True,
}


class RealSpeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def realspeed(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, race_number, universe = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, race_number, ctx.invoked_with in graph_commands, universe)


async def get_params(ctx, user, params, command=info):
    username = user["username"]
    race_number = None
    universe = user["universe"]

    if params and params[0].lower() != "me":
        username = params[0]

    # -realspeed -1 shorthand
    if user["username"] and params and params[0].startswith("-"):
        try:
            username = user["username"]
            race_number = utils.parse_value_string(params[0])
        except:
            pass

    if len(params) == 1:
        try:
            url = params[0]
            result = urlparse(url)
            if result.scheme and result.netloc:
                race_info = utils.get_race_link_info(url)
                if not race_info:
                    raise ValueError
                username, race_number, universe = race_info
        except ValueError:
            await ctx.send(embed=errors.invalid_param(command))
            raise

    elif len(params) > 1:
        try:
            race_number = utils.parse_value_string(params[1])
        except ValueError:
            await ctx.send(embed=errors.invalid_number_format())
            raise

    if not username:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    return username.lower(), race_number, universe


async def run(ctx, user, username, race_number, graph, universe, raw=False):
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    if race_number is None:
        race_number = stats["races"]

    elif race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race_info(username, race_number, get_lagged=True, get_raw=raw, universe=universe)
    if not race_info:
        return await ctx.send(embed=errors.race_not_found(username, race_number, universe))

    title = f"{'Raw' if raw else 'Real'} speeds"
    color = user["colors"]["embed"]
    lagged = race_info["lagged"]
    description = utils.text_description(race_info)

    reverse_lag = False
    if "unlagged" not in race_info:
        speeds_string = (
            f"**Lagged:** {lagged:,.2f} WPM\n\n"
            f"{title} not available for this race\n\n"
            f"Completed {utils.discord_timestamp(race_info['timestamp'])}"
        )

    else:
        unlagged = race_info["unlagged"]
        adjusted = race_info["adjusted"]

        if lagged > round(unlagged, 2):
            reverse_lag = True
            description = "\U0001F6A9 Reverse Lagged Score \U0001F6A9\n\n" + description
            color = colors.error

        speeds_string = (
            f"**Lagged:** {lagged:,.2f} WPM ({race_info['lag']:,.2f} WPM lag)\n"
            f"**Unlagged:** {unlagged:,.2f} WPM ({race_info['ping']:,}ms ping)\n"
            f"**Adjusted:** {adjusted:,.3f} WPM ({race_info['start']:,}ms start)\n"
            f"**Race Time:** {utils.format_duration_short(race_info['ms'] / 1000, False)}\n\n"
        )

        if raw:
            correction = race_info["correction"]
            correction_percent = (correction / race_info["ms"]) * 100
            speeds_string += (
                f"**Raw Unlagged:** {race_info['raw_unlagged']:,.2f} WPM\n"
                f"**Raw Adjusted:**  {race_info['raw_adjusted']:,.3f} WPM\n"
                f"**Correction Time:** {utils.format_duration_short(correction / 1000, False)} "
                f"({correction_percent:,.2f}%)\n\n"
            )

        speeds_string += f"Completed <t:{int(race_info['timestamp'])}:R>"

        if universe == "play" and 300 <= adjusted <= 450 and not stats["disqualified"]:
            races_300_list = races_300.get_races()
            in_list = False
            for race in races_300_list:
                if race["username"] == username and race["number"] == race_number:
                    in_list = True
                    break

            if not in_list:
                print(f"New 300 WPM! {username}|{race_number}")
                races_300.add_race({
                    "username": username,
                    "number": race_number,
                    "timestamp": race_info["timestamp"],
                    "wpm": race_info["lagged"],
                    "wpm_adjusted": race_info["adjusted"],
                })

    embed = Embed(
        title=f"{title.title()} - Race #{race_number:,}",
        description=description,
        url=urls.replay(username, race_number, universe) + f"{'&allowDisqualified=true' * stats['disqualified']}",
        color=color
    )

    utils.add_profile(embed, stats)
    utils.add_universe(embed, universe)

    embed.add_field(name="Speeds", value=speeds_string, inline=False)

    title = f"Race Graph - {username} - Race #{race_number:,}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    file_name = f"{username}_{race_number}.png"

    if graph:
        ranking = {"username": username}

        if raw:
            if ctx.invoked_with in ["rawadjustedgraph", "rag"]:
                y_label = "Raw Adjusted WPM"
                ranking["average_adjusted_wpm"] = race_info["raw_wpm_adjusted_over_keystrokes"]
                ranking["instant_chars"] = race_info["instant_chars"]

            else:
                y_label = "Raw WPM"
                ranking["average_wpm"] = race_info["raw_wpm_over_keystrokes"]

        elif ctx.invoked_with in ["adjustedgraph", "ag", "ag*"]:
            y_label = "Adjusted WPM"
            ranking["average_adjusted_wpm"] = race_info["wpm_adjusted_over_keystrokes"]
            ranking["instant_chars"] = race_info["instant_chars"]

        else:
            y_label = "WPM"
            ranking["average_wpm"] = race_info["wpm_over_keystrokes"]

        graphs.match(user, [ranking], title, y_label, file_name, limit_y="*" not in ctx.invoked_with)

        embed.set_image(url=f"attachment://{file_name}")
        file = File(file_name, filename=file_name)

        await ctx.send(embed=embed, file=file)

        os.remove(file_name)

    else:
        await ctx.send(embed=embed)

    recents.text_id = race_info["text_id"]

    if universe == "play" and reverse_lag:
        if username == "slowtexts":
            return
        modified_race = modified_races.get_race(username, race_number)
        if not modified_race:
            embed = Embed(
                title="Reverse Lag Detected",
                description="This score has been corrected in the database",
                color=colors.error,
            )
            await ctx.send(embed=embed)
            if await download(stats=stats, override=True):
                update_text_stats(username)
            await races.correct_race(username, race_number, race_info)


async def setup(bot):
    await bot.add_cog(RealSpeed(bot))
