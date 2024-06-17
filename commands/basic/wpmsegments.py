from discord import Embed, File
from discord.ext import commands
import errors
import graphs
import urls
import utils
from database.bot_users import get_user
from api.users import get_stats
from api.races import get_race_info
from commands.basic.realspeed import get_args

command = {
    "name": "wpmsegments",
    "aliases": ["ws"],
    "description": "Displays a bar graph of WPM segments over a race",
    "parameters": "[username] <race_number>",
    "usages": ["wpmsegments keegant 420"],
    "multiverse": True,
}


class WpmSegments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def wpmsegments(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, universe)


async def run(ctx, user, username, race_number, universe):
    stats = get_stats(username, universe=universe)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    if race_number < 1:
        race_number = stats["races"] + race_number

    race_info = await get_race_info(username, race_number, get_lagged=True, universe=universe, get_raw=True)
    if not race_info:
        return await ctx.send(embed=errors.race_not_found(username, race_number, universe))

    embed = Embed(
        title=f"WPM Segments - Race #{race_number:,}",
        color=user["colors"]["embed"],
        url=urls.replay(username, race_number, universe) + f"{'&allowDisqualified=true' * stats['disqualified']}",
    )
    utils.add_profile(embed, stats)
    utils.add_universe(embed, universe)

    quote = race_info["quote"]
    text_segments = utils.get_segments(quote)
    delays = race_info["delays"]
    raw_delays = race_info["raw_delays"]
    multiplier = utils.get_universe_multiplier(universe)
    segments = []

    index = 0
    for text in text_segments:
        segment_delays = delays[index:len(text) + index]
        segment_raw_delays = raw_delays[index:len(text) + index]
        wpm = multiplier * len(text) / sum(segment_delays)
        raw_wpm = multiplier * len(text) / sum(segment_raw_delays)
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
    )
    for segment in segments:
        segment_text = utils.escape_discord_format(segment["text"]).replace("-", "\\-")
        description += f"**{segment['wpm']:,.2f} WPM**"
        if segment["wpm"] < segment["raw_wpm"]:
            description += f" **({segment['raw_wpm']:,.2f} Raw)**"
        description += f"\n{segment_text}\n"

    description += f"\nCompleted {utils.discord_timestamp(race_info['timestamp'])}"
    embed.description = description

    file_name = f"race_wpm_{username}.png"
    title = f"WPM Segments - {username} - Race #{race_number:,}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    graphs.race_wpm(user, segments, title, file_name)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    utils.remove_file(file_name)


async def setup(bot):
    await bot.add_cog(WpmSegments(bot))
