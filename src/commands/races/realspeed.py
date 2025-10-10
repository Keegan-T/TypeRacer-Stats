from discord.ext import commands

import database.bot.recent_text_ids as recent
from api.users import get_stats
from commands.account.download import run as download
from config import prefix
from database.bot.users import get_user
from database.main import users, races
from graphs import match_graph
from utils import errors, urls, strings, embeds
from utils.embeds import Page, Message
from utils.strings import real_speed_fields

graph_commands = ["realspeedgraph", "rg", "adjustedgraph", "ag", "ag*"]
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
    ],
}


class RealSpeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def realspeed(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command, ctx.channel.id)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, ctx.invoked_with in graph_commands, universe)


def get_args(user, args, info, channel_id):
    params = "username int:0"
    universe = user["universe"]

    result = strings.parse_command(user, params, args, info, channel_id)
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
    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    stats = await get_stats(username, universe=universe)
    await download(racer=stats, universe=universe)

    if race_number < 1:
        race_number = stats["races"] + race_number

    race = await races.get_race(username, race_number, universe, get_log=True, get_keystrokes=True, get_typos=True)
    if not race:
        return await ctx.send(embed=errors.race_not_found(username, race_number, universe))
    if raw and not race.get("raw_adjusted", None):
        return await ctx.send(embed=errors.raw_speeds_unavailable(username, race_number, universe))

    description = f"Completed {strings.discord_timestamp(race['timestamp'])}" + "\n\n" + strings.text_description(race, universe)
    footer = ""
    if race.get("distributed", None):
        footer = "Adjusted speed recalculated to account for lag at the start of the race"

    render = None
    if graph:
        if not race.get("keystroke_wpm", None):
            return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))
        ranking = {"username": username}
        if ctx.invoked_with in ["adjustedgraph", "ag", "ag*"]:
            y_label = "Adjusted WPM"
            ranking["keystroke_wpm"] = race["keystroke_wpm_adjusted"]

        else:
            y_label = "WPM"
            ranking["keystroke_wpm"] = race["keystroke_wpm"]

        def render():
            return match_graph.render(
                user, [ranking], f"Race Graph - {username} - Race #{race_number:,}",
                y_label, universe, limit_y="*" not in ctx.invoked_with
            )

    page = Page(
        title=f"{'Raw' if raw else 'Real'} Speeds - Race #{race_number:,}",
        description=description,
        fields=real_speed_fields(race, raw),
        render=render,
    )

    message = Message(
        ctx, user, page,
        url=urls.replay(username, race_number, universe, stats["disqualified"]),
        footer=footer,
        profile=stats,
        universe=universe,
    )

    await message.send()

    recent.update_recent(ctx.channel.id, race["text_id"])


async def setup(bot):
    await bot.add_cog(RealSpeed(bot))
