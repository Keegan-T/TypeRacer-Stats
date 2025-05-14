from discord import Embed, File
from discord.ext import commands

import commands.recent as recent
import database.races_300 as races_300
from api.races import get_race
from api.users import get_stats
from commands.basic.realspeed import get_args
from config import prefix
from database.bot_users import get_user
from graphs import match_graph
from graphs.core import remove_file
from utils import errors, urls, strings, embeds

command = {
    "name": "rawcomparison",
    "aliases": ["rc", "poem"],
    "description": "Displays an overlay of adjusted and raw adjusted speed of a race\n"
                   f"`{prefix}rawcomparison [username] <-n>` will display the comparison for n races ago",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number"
    },
    "usages": [
        "rawcomparison poem 222222",
        "rawcomparison storm -1",
        "rawcomparison https://data.typeracer.com/pit/result?id=|tr:keegant|1000000",
    ],
}


class RawComparison(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def rawcomparison(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, universe)


async def run(ctx, user, username, race_number, universe):
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    elif race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race(username, race_number, get_raw=True, universe=universe)
    if not race_info or "unlagged" not in race_info:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))

    description = strings.text_description(race_info)
    speeds_string = strings.real_speed_description(race_info)
    speeds_string += strings.raw_speed_description(race_info)
    speeds_string += strings.discord_timestamp(race_info["timestamp"])

    if universe == "play" and 300 <= race_info["adjusted"] <= 450 and not stats["disqualified"]:
        await races_300.add_new_race(username, race_number, race_info)

    embed = Embed(
        title=f"Real vs. Raw Speed - Race #{race_number:,}",
        description=description,
        url=urls.replay(username, race_number, universe, stats["disqualified"]),
        color=user["colors"]["embed"],
    )

    embeds.add_profile(embed, stats)
    embeds.add_universe(embed, universe)

    embed.description += f"\n\n{speeds_string}"

    title = f"Race Graph - {username} - Race #{race_number:,}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    file_name = f"real_vs_raw_{username}_{race_number}.png"

    rankings = [
        {
            "username": "Raw Adjusted",
            "average_wpm": race_info["raw_wpm_adjusted_over_keystrokes"],
        },
        {
            "username": "Adjusted",
            "average_wpm": race_info["wpm_adjusted_over_keystrokes"],
        }
    ]

    y_label = "Adjusted vs. Raw WPM"

    match_graph.render(user, rankings, title, y_label, file_name)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    remove_file(file_name)

    recent.text_id = race_info["text_id"]


async def setup(bot):
    await bot.add_cog(RawComparison(bot))
