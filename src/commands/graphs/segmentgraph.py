from discord.ext import commands

import database.bot.recent_text_ids as recent
from api.races import get_universe_multiplier
from api.users import get_stats
from commands.account.download import run as download
from commands.races.realspeed import get_args
from database.bot.users import get_user
from database.main import users, races
from graphs import segment_graph
from utils import errors, urls, strings
from utils.embeds import Page, Message, is_embed, Field
from utils.stats import calculate_wpm

command = {
    "name": "segmentgraph",
    "aliases": ["segments", "seg", "sg", "wpmsegments", "ws", "wordgraph", "words", "wg"],
    "description": "Displays a bar graph of WPM segments over a race",
    "parameters": "[username] <race_number>",
    "usages": ["segmentgraph keegant 420"],
}


class SegmentGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def segmentgraph(self, ctx, *args):
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

    race = races.get_race(username, race_number, universe, get_log=True)
    if not race or not race["wpm_raw"]:
        return await ctx.send(embed=errors.race_not_found(username, race_number, universe))

    def format_segment(segment):
        segment_text = segment["text"]
        if len(segment_text) > 100:
            segment_text = f"{segment_text[:100]}..."

        wpm = segment["wpm"]
        raw_wpm = segment["raw_wpm"]
        wpm_text = f"**{wpm:,.2f}**"
        if raw_wpm > wpm:
            wpm_text = f"**[{wpm:,.2f}](http://a \"{raw_wpm:,.2f} Raw\")**"
        return f"{wpm_text} - {strings.escape_formatting(segment_text)}"

    quote = race["quote"]
    delays = race["delays"]
    raw_delays = race["raw_delays"]
    text_segments = strings.get_segments(quote)
    multiplier = get_universe_multiplier(universe)
    segments = []

    i = 0
    for text in text_segments:
        segment_delays = delays[i:len(text) + i]
        raw_segment_delays = raw_delays[i:len(text) + i]
        wpm = calculate_wpm(segment_delays, sum(segment_delays), multiplier)
        raw_wpm = calculate_wpm(raw_segment_delays, sum(raw_segment_delays), multiplier)
        segments.append({
            "text": text,
            "wpm": wpm,
            "raw_wpm": raw_wpm,
        })
        i += len(text)

    description = (
        f"{strings.text_description(race, universe).split("\n")[0]}\n\n"
        f"**Speed:** {race['unlagged']:,.2f} WPM "
        f"({race['accuracy']:.1%} Accuracy)\n"
        f"**Raw Speed:** {race['raw_unlagged']:,.2f} WPM"
    )
    timestamp_string = f"Completed {strings.discord_timestamp(race['timestamp'])}"
    segment_description = (
        f"{description}\n\n"
        f"**WPM - Segment**\n"
    )
    segment_description += "\n".join(format_segment(segment) for segment in segments)
    segment_description += "\n\n" + timestamp_string

    word_segments = []
    words = quote.split()
    i = 0
    for word in words:
        chars = len(word)
        word_delays = delays[i + 1:i + chars]
        raw_word_delays = raw_delays[i + 1:i + chars]
        wpm = calculate_wpm(word_delays, sum(word_delays), multiplier)
        raw_wpm = calculate_wpm(raw_word_delays, sum(raw_word_delays), multiplier)
        word_segments.append({
            "text": word,
            "wpm": wpm,
            "raw_wpm": raw_wpm,
        })
        i += chars + 1

    word_segments = [word for word in word_segments if word["wpm"] != float("inf")]
    fastest = sorted(word_segments, key=lambda x: -x["wpm"])
    slowest = fastest[::-1]

    segment_page = Page(
        title=f"WPM Segments - Race #{race_number:,}",
        description=segment_description,
        render=lambda: segment_graph.render(
            user, segments, f"WPM Segments - {username} - Race #{race_number:,}",
            "Words", universe
        ),
        button_name="Segments",
    )

    word_page = Page(
        title=f"Words - Race #{race_number:,}",
        description=description + "\n\n" + timestamp_string,
        fields=[
            Field(
                name="Fastest",
                value="\n".join(format_segment(word) for word in fastest[:10]),
            ),
            Field(
                name="Slowest",
                value="\n".join(format_segment(word) for word in slowest[:10]),
            )
        ],
        render=lambda: segment_graph.render(
            user, word_segments, f"Words - {username} - Race #{race_number:,}",
            "Words", universe
        ),
        button_name="Words",
        default=ctx.invoked_with in ["wordgraph", "words", "wg"],
    )

    message = Message(
        ctx, user, [segment_page, word_page],
        url=urls.replay(username, race_number, universe, stats["disqualified"]),
        profile=stats,
        universe=universe,
    )

    await message.send()

    recent.update_recent(ctx.channel.id, race["text_id"])


async def setup(bot):
    await bot.add_cog(SegmentGraph(bot))
