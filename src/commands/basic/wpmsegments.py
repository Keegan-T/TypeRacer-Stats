from discord import Embed, File
from discord.ext import commands

from api.races import get_race, get_universe_multiplier
from api.users import get_stats
from commands.basic.realspeed import get_args
from database.bot_users import get_user
from graphs import segment_graph
from graphs.core import remove_file
from utils import errors, urls, strings, embeds

command = {
    "name": "wpmsegments",
    "aliases": ["segments", "ws"],
    "description": "Displays a bar graph of WPM segments over a race",
    "parameters": "[username] <race_number>",
    "usages": ["wpmsegments keegant 420"],
}


class WpmSegments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def wpmsegments(self, ctx, *args):
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

    race_info = await get_race(username, race_number, universe=universe, get_raw=True)
    if not race_info:
        return await ctx.send(embed=errors.race_not_found(username, race_number, universe))

    embed = Embed(
        title=f"WPM Segments - Race #{race_number:,}",
        color=user["colors"]["embed"],
        url=urls.replay(username, race_number, universe, stats["disqualified"]),
    )
    embeds.add_profile(embed, stats)
    embeds.add_universe(embed, universe)

    quote = race_info["quote"]
    text_segments = strings.get_segments(quote)
    if "delays" not in race_info:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))
    delays = race_info["delays"]
    raw_delays = race_info["raw_delays"]
    multiplier = get_universe_multiplier(universe)
    segments = []

    index = 0
    for text in text_segments:
        segment_delays = delays[index:len(text) + index]
        segment_raw_delays = raw_delays[index:len(text) + index]
        try:
            wpm = multiplier * len(text) / sum(segment_delays)
        except ZeroDivisionError:
            wpm = float("inf")
        try:
            raw_wpm = multiplier * len(text) / sum(segment_raw_delays)
        except ZeroDivisionError:
            raw_wpm = float("inf")
        segments.append({
            "text": text,
            "wpm": wpm,
            "raw_wpm": raw_wpm,
        })
        index += len(text)

    text_id = race_info["text_id"]
    words = len(quote.split(" "))
    chars = len(quote)
    description = (
        f"**Text** - [#{text_id}]"
        f"({urls.trdata_text(text_id)}) - "
        f"{words:,} words - {chars:,} characters\n\n"
        f"**Speed:** {race_info['unlagged']:,.2f} WPM "
        f"({race_info['accuracy']:.1%} Accuracy)\n"
        f"**Raw Speed:** {race_info['raw_unlagged']:,.2f} WPM\n\n"
    )
    for segment in segments:
        segment_text = strings.escape_formatting(segment["text"]).replace("-", "\\-")
        if len(segment_text) > 100:
            segment_text = f"{segment_text[:100]}..."
        description += f"**{segment['wpm']:,.2f} WPM"
        if segment["wpm"] < segment["raw_wpm"]:
            description += f" ({segment['raw_wpm']:,.2f} Raw)"
        description += f":** {segment_text}\n"

    description += f"\nCompleted {strings.discord_timestamp(race_info['timestamp'])}"
    embed.description = description

    title = f"WPM Segments - {username} - Race #{race_number:,}"
    file_name = segment_graph.render(user, segments, title, universe)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    remove_file(file_name)


async def setup(bot):
    await bot.add_cog(WpmSegments(bot))
