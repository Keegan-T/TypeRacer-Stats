from discord import Embed, File
from discord.ext import commands
import graphs
import utils
import errors
import urls
from config import prefix
from database.bot_users import get_user
from api.users import get_stats
from api.races import get_race_info
import commands.recent as recent
import database.races_300 as races_300
from commands.basic.realspeed import get_args

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
    "multiverse": True,
}


class RawComparison(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def rawcomparison(self, ctx, *args):
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

    elif race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race_info(username, race_number, get_raw=True, universe=universe)
    if not race_info or "unlagged" not in race_info:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))

    lagged = race_info["lagged"]
    unlagged = race_info["unlagged"]
    adjusted = race_info["adjusted"]
    description = utils.text_description(race_info)

    speeds_string = (
        f"**Lagged:** {lagged:,.2f} WPM ({race_info['lag']:,.2f} WPM lag)\n"
        f"**Unlagged:** {unlagged:,.2f} WPM ({race_info['ping']:,}ms ping)\n"
        f"**Adjusted:** {adjusted:,.3f} WPM ({race_info['start']:,}ms start)\n"
        f"**Race Time:** {utils.format_duration_short(race_info['ms'] / 1000, False)}\n\n"
    )

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
        races_300.add_new_race(username, race_number, race_info)

    embed = Embed(
        title=f"Real vs. Raw Speed - Race #{race_number:,}",
        description=description,
        url=urls.replay(username, race_number, universe) + f"{'&allowDisqualified=true' * stats['disqualified']}",
        color=user["colors"]["embed"],
    )

    utils.add_profile(embed, stats)
    utils.add_universe(embed, universe)

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

    graphs.match(user, rankings, title, y_label, file_name)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    utils.remove_file(file_name)

    recent.text_id = race_info["text_id"]


async def setup(bot):
    await bot.add_cog(RawComparison(bot))
