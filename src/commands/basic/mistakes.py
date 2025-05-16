from discord import Embed, File
from discord.ext import commands

import commands.recent as recent
from api.races import get_race
from api.users import get_stats
from commands.basic.realspeed import get_args
from config import prefix
from database.bot_users import get_user
from graphs import match_graph
from graphs.core import remove_file
from utils import errors, embeds, strings, urls, colors

command = {
    "name": "mistakes",
    "aliases": ["typos", "ty", "x"],
    "description": "Displays the typos on a graph for a user's race\n"
                   f"`{prefix}mistakes [username] <-n>` will return real speeds for n races ago\n",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number"
    },
    "usages": [
        "mistakes keegant 100000",
        "mistakes keegant -1",
        "mistakes https://data.typeracer.com/pit/result?id=|tr:keegant|1000000",
    ],
}


class Mistakes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def mistakes(self, ctx, *args):
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

    if race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race(username, race_number, universe=universe, get_typos=True)
    if not race_info or "unlagged" not in race_info:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))

    lagged = race_info["lagged"]
    unlagged = race_info["unlagged"]
    adjusted = race_info["adjusted"]

    typos = race_info["typos"]
    quote = list(race_info["quote"])
    for offset, typo in enumerate(typos):
        quote.insert(typo[1] + offset, "\\❌")
    race_info["quote"] = "".join(quote)

    description = strings.text_description(race_info)

    color = user["colors"]["embed"]
    if len(typos) == 0:
        description += "\n\nNo mistakes!"
        color = colors.success

    speeds_string = (
        f"**Lagged:** {lagged:,.2f} WPM ({race_info['lag']:,.2f} WPM lag)\n"
        f"**Unlagged:** {unlagged:,.2f} WPM ({race_info['ping']:,}ms ping)\n"
        f"**Adjusted:** {adjusted:,.3f} WPM ({race_info['start']:,}ms start)\n"
        f"**Race Time:** {strings.format_duration_short(race_info['ms'] / 1000, False)}\n"
        f"**Mistakes:** {len(typos):,}\n\n"
        f"Completed {strings.discord_timestamp(race_info['timestamp'])}"
    )

    embed = Embed(
        title=f"Mistakes - Race #{race_number:,}",
        description=description + f"\n\n{speeds_string}",
        url=urls.replay(username, race_number, universe, stats['disqualified']),
        color=color,
    )

    embeds.add_profile(embed, stats)
    embeds.add_universe(embed, universe)

    title = f"Race Graph - {username} - Race #{race_number:,}"
    file_name = f"mistakes_{username}_{race_number}.png"

    rankings = [{"username": username, "average_wpm": race_info["wpm_adjusted_over_keystrokes"]}]
    y_label = "Adjusted WPM"

    match_graph.render(user, rankings, title, y_label, universe, typos=race_info["typos"])

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    remove_file(file_name)

    recent.text_id = race_info["text_id"]


async def setup(bot):
    await bot.add_cog(Mistakes(bot))
