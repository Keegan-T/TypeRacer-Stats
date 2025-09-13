from collections import defaultdict

from discord.ext import commands

import database.bot.recent_text_ids as recent
from api.users import get_stats
from commands.account.download import run as download
from commands.races.realspeed import get_args
from config import prefix
from database.bot.users import get_user
from database.main import users, races
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
    ],
}


class Mistakes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def mistakes(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command, ctx.channel.id)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, universe)


async def run(ctx, user, username, race_number, universe):
    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    stats = get_stats(username, universe=universe)
    await download(racer=stats, universe=universe)

    if race_number < 1:
        race_number = stats["races"] + race_number

    race = races.get_race(username, race_number, universe, get_log=True, get_keystrokes=True, get_typos=True)
    if not race or "typos" not in race:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))

    typos = race["typos"]
    markers = defaultdict(str)
    for typo in typos:
        markers[typo[1]] += "\\❌"

    quote = race["quote"]
    race["quote"] = get_marked_quote(quote, markers)
    typo_description = strings.text_description(race, universe) + "\n\n"

    pauses = race["pauses"]
    for pause in pauses:
        markers[pause] += "\\⏸️"
    race["quote"] = get_marked_quote(quote, markers)
    pause_description = strings.text_description(race, universe) + "\n\n"

    speed_string = strings.real_speed_description(race)
    typo_count = len(typos)
    pause_count = len(pauses)
    typo_string = f"**Mistakes:** {typo_count:,}\n"
    pause_string = f"**Pauses:** {pause_count:,}\n"
    completed_string = f"\nCompleted {strings.discord_timestamp(race['timestamp'])}"
    typo_description += speed_string + typo_string + completed_string
    pause_description += speed_string + typo_string + pause_string + completed_string

    title = f"Race Graph - {username} - Race #{race_number:,}"
    rankings = [{
        "username": username,
        "keystroke_wpm": race["keystroke_wpm_adjusted"]
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
            typos=typos, markers=[[], race["pauses"]]
        ),
        button_name="With Pauses",
        default=ctx.invoked_with in ["pauses", "xp"],
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

    recent.update_recent(ctx.channel.id, race["text_id"])


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
