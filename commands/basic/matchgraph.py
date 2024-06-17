from discord import Embed, File
from discord.ext import commands
import graphs
import utils
import errors
import urls
from config import prefix
from database.bot_users import get_user
from api.users import get_stats
from api.races import get_match
from commands.basic.realspeed import get_args
from commands.locks import match_lock
from commands.basic.realspeedaverage import command_in_use
import commands.recent as recent

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
    "multiverse": True,
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

    match = await get_match(username, race_number, universe)
    if not match:
        return await ctx.send(embed=errors.logs_not_found(username, race_number, universe))

    description = utils.text_description(match) + "\n\n**Rankings**\n"

    for i, race in enumerate(match["rankings"]):
        racer_username = utils.escape_discord_format(race["username"])
        description += (
            f"{i + 1}. {racer_username} - "
            f"[{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['race_number'], universe)}) "
            f"({race['accuracy'] * 100:,.1f}% Acc, "
            f"{race['start']:,}ms start)\n"
        )

    description += f"\nCompleted {utils.discord_timestamp(match['timestamp'])}"

    embed = Embed(
        title=f"Match Graph - Race #{race_number:,}",
        description=description,
        url=urls.replay(username, race_number, universe),
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats, pfp=False)
    utils.add_universe(embed, universe)

    title = f"Match Graph - {username} - Race #{race_number:,}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    file_name = f"match_{username}_{race_number}.png"
    graphs.match(user, match["rankings"], title, "WPM", file_name, limit_y="*" not in ctx.invoked_with)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    utils.remove_file(file_name)

    recent.text_id = match["text_id"]


async def setup(bot):
    await bot.add_cog(MatchGraph(bot))
