from discord.ext import commands

import database.bot.recent_text_ids as recent
from api.races import get_race_by_id
from api.users import get_stats
from commands.account.download import run as download
from commands.races.realspeed import get_args
from commands.locks import match_lock
from config import prefix
from database.bot.users import get_user
from database.main import races, users, texts
from graphs import match_graph
from utils import errors, urls, strings
from utils.embeds import Message, Page, is_embed
from utils.errors import command_in_use

command = {
    "name": "matchgraph",
    "aliases": ["mg", "mg*"],
    "description": "Displays a graph of up to 10 user's unlagged WPM in a race\n"
                   f"`{prefix}matchgraph [username] <-n>` will display the match graph for n races ago",
    "parameters": "[username] <race_number>",
    "defaults": {
        "race_number": "the user's most recent race number",
    },
    "usages": [
        "matchgraph keegant 1000000",
        "realspeed keegant -1",
    ],
}


class MatchGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def matchgraph(self, ctx, *args):
        if match_lock.locked():
            return await ctx.send(embed=command_in_use())

        async with match_lock:
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

    stats = await get_stats(username, universe=universe)
    await download(racer=stats, universe=universe)

    if race_number < 1:
        race_number = stats["races"] + race_number

    race = await races.get_race(username, race_number, universe)
    if not race or not race["wpm_raw"]:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))
    race_id = race["race_id"]
    match = await get_race_by_id(race_id)
    if not match:
        return await ctx.send(embed=errors.match_info_unavailable(username, race_number, universe))

    text_description = strings.text_description(texts.get_text(race["text_id"], universe), universe)
    description = text_description + "\n\n**Rankings**\n"
    raw_description = text_description + "\n\n**Raw Rankings**\n"
    pauseless_description = text_description + "\n\n**Pauseless Rankings**\n"

    for i, race in enumerate(match["rankings"][:10]):
        racer_username = strings.escape_formatting(race["username"])
        description += (
            f"{i + 1}. {racer_username} - "
            f"[{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['number'], universe, timestamp=race['timestamp'])}) "
            f"({race['accuracy']:.2%} Acc, "
            f"{race['start']:,.0f}ms start)\n"
        )

    for i, race in enumerate(match["raw_rankings"][:10]):
        racer_username = strings.escape_formatting(race["username"])
        raw_description += (
            f"{i + 1}. {racer_username} - "
            f"[{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['number'], universe, timestamp=race['timestamp'])}) "
            f"({race['correction_percent']:.1%} Corr, "
            f"{race['pause_percent']:.1%} Pause)\n"
        )

    for i, race in enumerate(match["pauseless_rankings"][:10]):
        racer_username = strings.escape_formatting(race["username"])
        pauseless_description += (
            f"{i + 1}. {racer_username} - "
            f"[{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['number'], universe, timestamp=race['timestamp'])}) "
            f"({race['correction_percent']:.1%} Corr, "
            f"{race['pause_percent']:.1%} Pause)\n"
        )

    completed = f"\nCompleted {strings.discord_timestamp(match['timestamp'])}"
    description += completed
    raw_description += completed
    pauseless_description += completed
    title = f"Match Graph - Race #{race_number:,}"
    graph_title = f"Match Graph - {username} - Race #{race_number:,}"
    url = urls.replay(username, race_number, universe, timestamp=race['timestamp'])

    def render(key):
        return lambda: match_graph.render(
            user, match[key], graph_title, "WPM", universe,
            limit_y="*" not in ctx.invoked_with
        )

    pages = [
        Page(title, description, button_name="Rankings", render=render("rankings")),
        Page(title, raw_description, button_name="Raw Rankings", render=render("raw_rankings")),
        Page(title, pauseless_description, button_name="Pauseless Rankings", render=render("pauseless_rankings")),
    ]

    message = Message(
        ctx, user, pages,
        url=url,
        profile=stats,
        universe=universe,
        show_pfp=False,
    )

    await message.send()

    recent.update_recent(ctx.channel.id, match["text_id"])


async def setup(bot):
    await bot.add_cog(MatchGraph(bot))
