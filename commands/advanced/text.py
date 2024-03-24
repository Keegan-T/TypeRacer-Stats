from discord import Embed, File
from discord.ext import commands
import os
import commands.recent as recents
from src import colors, graphs, urls, errors, utils
from src.config import prefix
from database.bot_users import get_user
from api.users import get_stats
import database.texts as texts
import database.races as races
import database.users as users
from commands.basic.download import download, update_text_stats
import database.text_results as top_tens

info = {
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
    "import": True,
}


class Text(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def text(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, text_id = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, text_id)


async def get_params(ctx, user, params):
    username = user["username"]
    text_id = None

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        text_id = params[1]
        if text_id == "^":
            text_id = recents.text_id

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), text_id


async def run(ctx, user, username, text_id=None, race_number=None):
    db_stats = users.get_user(username)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username))

    api_stats = get_stats(username)
    new_races = await download(stats=api_stats)

    graph = ctx.invoked_with in ["textgraph", "tg", "racetextgraph", "rtg"]

    if text_id is None:
        if race_number is None:
            race_number = api_stats["races"]

        if race_number < 1:
            race_number = api_stats["races"] + race_number

        race = races.get_race(username, race_number)

        if not race:
            return await ctx.send(embed=errors.race_not_found())

        text_id = race["text_id"]

    text = texts.get_text(text_id)
    if not text:
        return await ctx.send(embed=errors.unknown_text())

    title = "Text History"
    if ctx.invoked_with in ["racetext", "rt", "racetextgraph", "rtg"]:
        title += f" (Race #{race_number:,})"
    embed = Embed(title=title, url=urls.trdata_text_races(username, text_id))
    utils.add_profile(embed, api_stats)
    color = user["colors"]["embed"]

    description = utils.text_description(dict(text))

    race_list = races.get_text_races(username, text_id)
    if not race_list:
        embed.description = (description + "\n\nUser has no races on this text\n"
                                           f"[Race this text]({text['ghost']})")
        embed.color = color
        return await ctx.send(embed=embed)

    times_typed = len(race_list)
    wpm = [race["wpm"] for race in race_list]
    average = sum(wpm) / times_typed
    recent = race_list[-1]

    stats_string = f"**Times Typed:** {times_typed:,}\n"

    if times_typed > 1:
        best = max(race_list, key=lambda r: r["wpm"])
        worst = min(race_list, key=lambda r: r["wpm"])
        previous_best = max(race_list[:-1], key=lambda r: r["wpm"])
        if recent["wpm"] > previous_best["wpm"]:
            description = (
                    f"**Recent Personal Best!** {recent['wpm']:,.2f} WPM (+" +
                    f"{recent['wpm'] - previous_best['wpm']:,.2f} WPM)\n\n" +
                    description
            )

            color = colors.success
            stats_string += (
                f"**Average:** {average:,.2f} WPM\n"
                f"**Previous Best:** [{previous_best['wpm']:,.2f} WPM]"
                f"({urls.replay(username, previous_best['number'])}) - "
                f"<t:{int(previous_best['timestamp'])}:R>\n"
                f"**Worst:** [{worst['wpm']:,.2f} WPM]({urls.replay(username, worst['number'])}) - "
                f"<t:{int(worst['timestamp'])}:R>\n"
                f"**Recent:** [{recent['wpm']:,.2f} WPM]({urls.replay(username, recent['number'])}) - "
                f"<t:{int(recent['timestamp'])}:R>"
            )
        else:
            stats_string += (
                f"**Average:** {average:,.2f} WPM\n"
                f"**Best:** [{best['wpm']:,.2f} WPM]({urls.replay(username, best['number'])}) - "
                f"<t:{int(best['timestamp'])}:R>\n"
                f"**Worst:** [{worst['wpm']:,.2f} WPM]({urls.replay(username, worst['number'])}) - "
                f"<t:{int(worst['timestamp'])}:R>\n"
                f"**Recent:** [{recent['wpm']:,.2f} WPM]({urls.replay(username, recent['number'])}) - "
                f"<t:{int(recent['timestamp'])}:R>"
            )

    else:
        color = colors.success
        description = f"**New Text!**\n\n" + description
        stats_string += (
            f"**Recent:** [{recent['wpm']:,.2f} WPM]"
            f"({urls.replay(username, recent['number'])}) - "
            f"<t:{int(recent['timestamp'])}:R>"
        )

    embed.add_field(name="Stats", value=stats_string)

    embed.description = description
    embed.color = color

    # utils.time_start()
    # top_10 = texts.get_top_10(text_id)
    # print(top_10)
    # utils.time_end()

    if graph:
        title = f"WPM Improvement - {username} - Text #{text_id}"
        file_name = f"{username}_text_{text_id}_improvement.png"
        graphs.improvement(user, wpm, title, file_name)

        embed.set_image(url=f"attachment://{file_name}")
        file = File(file_name, filename=file_name)

        await ctx.send(embed=embed, file=file)

        os.remove(file_name)

    else:
        await ctx.send(embed=embed)

    await top_tens.update_results(text_id)
    top_10 = top_tens.get_top_10(text_id)
    top_10_score = next((score for score in top_10 if score["id"] == recent["id"]), None)

    if top_10_score:
        description = ""
        position = 0
        for i, race in enumerate(top_10):
            bold = ""
            if race["id"] == recent["id"]:
                bold = "**"
                position = i + 1
            username = race["username"]
            description += (
                f"{bold}{utils.rank(i + 1)} {utils.escape_discord_format(username)} - [{race['wpm']:,.2f} WPM]"
                f"({urls.replay(username, race['number'])}){bold} - "
                f"{utils.discord_timestamp(race['timestamp'])}\n"
            )

        embed = Embed(
            title=f"Top {position} Score! :tada:",
            description=description,
            color=colors.success,
        )

        await ctx.send(embed=embed)

    recents.text_id = text_id
    if new_races:
        update_text_stats(username)


async def setup(bot):
    await bot.add_cog(Text(bot))
