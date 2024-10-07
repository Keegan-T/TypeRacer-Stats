from discord import Embed, File
from discord.ext import commands

import commands.recent as recent
import database.races as races
import database.text_results as top_tens
import database.texts as texts
import database.users as users
from api.users import get_stats
from commands.basic.download import run as download
from config import prefix
from database.bot_users import get_user
from graphs import improvement_graph
from graphs.core import remove_file
from utils import errors, colors, urls, strings, embeds

command = {
    "name": "text",
    "aliases": ["t", "textgraph", "tg", "personalbest", "pb"],
    "description": "Displays a user's stats about a specific text\n"
                   f"`{prefix}text [username] ^` will use the most recent globally used text id\n"
                   f"`{prefix}textgraph` will add an improvement graph",
    "parameters": "[username] <text_id>",
    "defaults": {
        "text_id": "the text ID of the user's most recent race",
    },
    "usages": ["text keegant 3810446"],
}


class Text(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def text(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, text_id = result
        if text_id == -1:
            text_id = None
        await run(ctx, user, username, text_id)


def get_args(user, args, info):
    # Shorthand (-text ^)
    if len(args) == 1 and args[0] == "^" and user["username"]:
        return user["username"], recent.text_id

    params = "username text_id:-1"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, text_id=None, race_number=None):
    universe = user["universe"]
    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    api_stats = get_stats(username, universe=universe)
    await download(stats=api_stats, universe=universe)
    if era_string:
        api_stats = await users.time_travel_stats(api_stats, user)

    graph = ctx.invoked_with in ["textgraph", "tg", "racetextgraph", "rtg"]

    if text_id is None:
        if race_number is None:
            race_number = api_stats["races"]

        if race_number < 1:
            race_number = api_stats["races"] + race_number

        race = races.get_race(username, race_number, universe)

        if not race:
            return await ctx.send(embed=errors.race_not_found(username, race_number, universe))

        text_id = race["text_id"]

    text = texts.get_text(text_id, universe)
    if not text:
        return await ctx.send(embed=errors.unknown_text(universe))

    title = "Text History"
    if ctx.invoked_with in ["racetext", "rt", "racetextgraph", "rtg"]:
        title += f" (Race #{race_number:,})"
    embed = Embed(title=title, url=urls.trdata_text_races(username, text_id, universe))
    embeds.add_profile(embed, api_stats, universe)
    embeds.add_universe(embed, universe)
    color = user["colors"]["embed"]

    description = strings.text_description(dict(text), universe)

    race_list = races.get_text_races(
        username, text_id, universe, start_date=user["start_date"], end_date=user["end_date"]
    )
    if not race_list:
        embed.description = (
            f"{description}\n\nUser has no races on this text\n"
            f"[Race this text]({text['ghost']})"
        )
        embed.color = color
        recent.text_id = text_id
        return await ctx.send(embed=embed, content=era_string)

    times_typed = len(race_list)
    wpm = [race["wpm"] for race in race_list]
    average = sum(wpm) / times_typed
    recent_race = race_list[-1]

    stats_string = f"**Times Typed:** {times_typed:,}\n"

    if times_typed > 1:
        best = max(race_list, key=lambda r: r["wpm"])
        worst = min(race_list, key=lambda r: r["wpm"])
        previous_best = max(race_list[:-1], key=lambda r: r["wpm"])
        if recent_race["wpm"] > previous_best["wpm"]:
            description = (
                f"**Recent Personal Best!** {recent_race['wpm']:,.2f} WPM (+"
                f"{recent_race['wpm'] - previous_best['wpm']:,.2f} WPM)\n\n"
                f"{description}"
            )

            color = colors.success
            stats_string += (
                f"**Average:** {average:,.2f} WPM\n"
                f"**Previous Best:** [{previous_best['wpm']:,.2f} WPM]"
                f"({urls.replay(username, previous_best['number'], universe)}) - "
                f"<t:{int(previous_best['timestamp'])}:R>\n"
                f"**Worst:** [{worst['wpm']:,.2f} WPM]"
                f"({urls.replay(username, worst['number'], universe)}) - "
                f"<t:{int(worst['timestamp'])}:R>\n"
                f"**Recent:** [{recent_race['wpm']:,.2f} WPM]"
                f"({urls.replay(username, recent_race['number'], universe)}) - "
                f"<t:{int(recent_race['timestamp'])}:R>"
            )
        else:
            stats_string += (
                f"**Average:** {average:,.2f} WPM\n"
                f"**Best:** [{best['wpm']:,.2f} WPM]"
                f"({urls.replay(username, best['number'], universe)}) - "
                f"<t:{int(best['timestamp'])}:R>\n"
                f"**Worst:** [{worst['wpm']:,.2f} WPM]"
                f"({urls.replay(username, worst['number'], universe)}) - "
                f"<t:{int(worst['timestamp'])}:R>\n"
                f"**Recent:** [{recent_race['wpm']:,.2f} WPM]"
                f"({urls.replay(username, recent_race['number'], universe)}) - "
                f"<t:{int(recent_race['timestamp'])}:R>"
            )

    else:
        color = colors.success
        description = f"**New Text!**\n\n" + description
        stats_string += (
            f"**Recent:** [{recent_race['wpm']:,.2f} WPM]"
            f"({urls.replay(username, recent_race['number'], universe)}) - "
            f"<t:{int(recent_race['timestamp'])}:R>"
        )

    embed.description = description + f"\n\n{stats_string}"
    embed.color = color

    if graph:
        title = f"WPM Improvement - {username} - Text #{text_id}"
        file_name = f"text_improvement_{username}_{text_id}.png"
        improvement_graph.render(user, wpm, title, file_name, universe=universe)

        embed.set_image(url=f"attachment://{file_name}")
        file = File(file_name, filename=file_name)

        await ctx.send(embed=embed, file=file, content=era_string)

        remove_file(file_name)

    else:
        await ctx.send(embed=embed, content=era_string)

    recent.text_id = text_id

    if universe != "play" or user["end_date"]:
        return

    await top_tens.update_results(text_id)
    top_10 = top_tens.get_top_10(text_id)
    top_10_score = next((score for score in top_10 if score["id"] == recent_race["id"]), None)

    if not top_10_score:
        return

    description = ""
    title = ""
    for i, race in enumerate(top_10):
        style = ""
        if race["id"] == recent_race["id"]:
            style = "**"
            if i == 0:
                title = "Top Score! :trophy:"
            else:
                title = f"Top {i + 1} Score! :tada:"
        username = race["username"]
        description += (
            f"{strings.rank(i + 1)} {style}{strings.escape_discord_format(username)} - [{race['wpm']:,.2f} WPM]"
            f"({urls.replay(username, race['number'])}){style} - "
            f"{strings.discord_timestamp(race['timestamp'])}\n"
        )

    embed = Embed(
        title=title,
        description=description,
        color=colors.success,
    )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Text(bot))
