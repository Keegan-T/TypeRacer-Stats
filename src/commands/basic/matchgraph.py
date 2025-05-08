from discord.ext import commands

import commands.recent as recent
from api.races import get_match
from api.users import get_stats
from commands.basic.realspeed import get_args
from commands.locks import match_lock
from config import prefix
from database.bot_users import get_user
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
        "matchgraph https://data.typeracer.com/pit/result?id=play|tr:poem|200000"
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

    match = await get_match(username, race_number, universe)
    if not match:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))

    text_description = strings.text_description(match)
    description = text_description + "\n\n**Rankings**\n"
    raw_description = text_description + "\n\n**Raw Rankings**\n"

    for i, race in enumerate(match["rankings"]):
        racer_username = strings.escape_formatting(race["username"])
        description += (
            f"{i + 1}. {racer_username} - "
            f"[{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['race_number'], universe)}) "
            f"({race['accuracy'] * 100:,.1f}% Acc, "
            f"{race['start']:,}ms start)\n"
        )

    for i, race in enumerate(match["raw_rankings"]):
        racer_username = strings.escape_formatting(race["username"])
        raw_description += (
            f"{i + 1}. {racer_username} - "
            f"[{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['race_number'], universe)}) "
            f"({race['correction'] * 100:,.1f}% Corr, "
            f"{race['start']:,}ms start)\n"
        )

    completed = f"\nCompleted {strings.discord_timestamp(match['timestamp'])}"
    description += completed
    raw_description += completed
    title = f"Match Graph - Race #{race_number:,}"
    graph_title = f"Match Graph - {username} - Race #{race_number:,}"
    if universe != "play":
        graph_title += f"\nUniverse: {universe}"
    url = urls.replay(username, race_number, universe)

    def render(file_name):
        return match_graph.render(user, match["rankings"], graph_title, "WPM", file_name, limit_y="*" not in ctx.invoked_with)

    def render_raw(file_name):
        return match_graph.render(user, match["raw_rankings"], graph_title, "WPM", file_name, limit_y="*" not in ctx.invoked_with)

    def file_name(raw):
        raw_text = "_raw" * raw
        return f"match_{username}_{race_number}{raw_text}.png"

    pages = [
        Page(title, description, None, "Rankings", render, file_name(False)),
        Page(title, raw_description, None, "Raw Rankings", render_raw, file_name(True)),
    ]

    message = Message(
        ctx, user, pages,
        url=url,
        profile=stats,
        universe=universe,
        show_pfp=False,
    )

    await message.send()

    recent.text_id = match["text_id"]


async def setup(bot):
    await bot.add_cog(MatchGraph(bot))
