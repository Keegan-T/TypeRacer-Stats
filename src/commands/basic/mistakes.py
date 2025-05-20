from collections import defaultdict

from discord.ext import commands

import commands.recent as recent
from api.races import get_race
from api.users import get_stats
from commands.basic.realspeed import get_args
from config import prefix
from database.bot_users import get_user
from graphs import match_graph
from utils import errors, strings, urls, colors
from utils.embeds import Page, Message, is_embed

command = {
    "name": "mistakes",
    "aliases": ["typos", "ty", "x", "pauses", "xp"],
    "description": "Displays the typos on a graph for a user's race\n"
                   f"`{prefix}mistakes [username] <-n>` will return real speeds for n races ago\n"
                   f"`{prefix}pauses will include pauses in the graph\n",
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
        if is_embed(result):
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

    typos = race_info["typos"]
    markers = defaultdict(str)
    for typo in typos:
        markers[typo[1]] += "\\❌"

    quote = race_info["quote"]
    race_info["quote"] = get_marked_quote(quote, markers)
    typo_description = strings.text_description(race_info) + "\n\n"

    pauses = race_info["pauses"]
    for pause in pauses:
        markers[pause] += "\\⏸️"
    race_info["quote"] = get_marked_quote(quote, markers)
    pause_description = strings.text_description(race_info) + "\n\n"

    speed_string = (
        f"**Lagged:** {race_info['lagged']:,.2f} WPM ({race_info['lag']:,.2f} WPM lag)\n"
        f"**Unlagged:** {race_info['unlagged']:,.2f} WPM ({race_info['ping']:,}ms ping)\n"
        f"**Adjusted:** {race_info['adjusted']:,.3f} WPM ({race_info['start']:,}ms start)\n"
        f"**Race Time:** {strings.format_duration_short(race_info['duration'] / 1000, False)}\n"
    )

    typo_count = len(typos)
    pause_count = len(pauses)
    typo_string = f"**Mistakes:** {typo_count:,}\n"
    pause_string = f"**Pauses:** {pause_count:,}\n"
    completed_string = f"\nCompleted {strings.discord_timestamp(race_info['timestamp'])}"
    typo_description += speed_string + typo_string + completed_string
    pause_description += speed_string + typo_string + pause_string + completed_string

    title = f"Race Graph - {username} - Race #{race_number:,}"
    rankings = [{
        "username": username,
        "keystroke_wpm": race_info["keystroke_wpm_adjusted"]
    }]
    y_label = "Adjusted WPM"

    typo_page = Page(
        description=typo_description,
        render=lambda: match_graph.render(user, rankings, title, y_label, universe, typos=typos),
        button_name="Mistakes",
    )

    pause_page = Page(
        description=pause_description,
        render=lambda: match_graph.render(
            user, rankings, title, y_label, universe,
            typos=typos, markers=[[], race_info["pauses"]]
        ),
        button_name="With Pauses",
    )

    if not typo_count:
        typo_page.color = colors.success
        if not pause_count:
            pause_page.color = colors.success

    message = Message(
        ctx, user, [typo_page, pause_page],
        title=f"Mistakes - Race #{race_number:,}",
        url=urls.replay(username, race_number, universe, stats['disqualified']),
        profile=stats,
        universe=universe,
    )

    await message.send()

    recent.text_id = race_info["text_id"]


def get_marked_quote(quote, markers):
    characters = []
    for index, symbol in markers.items():
        characters.append([index - 0.5, symbol])
    for i, char in enumerate(quote):
        characters.append([i, char])
    characters.sort(key=lambda x: x[0])

    return "".join(x[1] for x in characters)


async def setup(bot):
    await bot.add_cog(Mistakes(bot))
