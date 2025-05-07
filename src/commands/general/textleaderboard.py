from discord import Embed
from discord.ext import commands

import api.texts as texts_api
import commands.recent as recent
import database.text_results as top_tens
import database.texts as texts
from database.bot_users import get_user
from utils import errors, urls, strings, embeds

command = {
    "name": "textleaderboard",
    "aliases": ["tlb", "10"],
    "description": "Displays the top 10 leaderboard for a text",
    "defaults": {
        "text_id": "the most recently viewed text ID"
    },
    "parameters": "<text_id>",
    "usages": ["textleaderboard 3810446"],
    "temporal": False,
}


class TextLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textleaderboard(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        text_id = result
        await run(ctx, user, text_id)


def get_args(user, args, info):
    params = "text_id"

    result = strings.parse_command(user, params, args, info)
    if embeds.is_embed(result):
        return result

    return result[0]


async def run(ctx, user, text_id):
    universe = user["universe"]
    text = texts.get_text(text_id, universe)
    if not text:
        return await ctx.send(embed=errors.unknown_text(universe))

    embed = Embed(
        title=f"Text #{text_id}",
        url=urls.trdata_text(text_id, universe),
        color=user["colors"]["embed"],
    )

    full_quote = text["quote"]
    characters = len(full_quote)
    words = len(full_quote.split(" "))
    quote = strings.truncate_clean(full_quote, 1000)
    embed.description = (
        f'{words:,} words - {characters:,} characters - '
        f'[Ghost]({text["ghost"]})\n"{quote}"\n\n**Top 10**\n'
    )

    text_id = int(text_id)
    disabled_text_ids = texts.get_disabled_text_ids()

    if text_id in disabled_text_ids or universe != "play":
        top_10 = await texts_api.get_top_10(text_id, universe)
        for i, score in enumerate(top_10):
            race, user = score
            username = user["id"][3:]
            embed.description += (
                f"{strings.rank(i + 1)} {strings.escape_formatting(username)} - [{race['wpm']:,.2f} WPM]"
                f"({urls.replay(username, race['gn'], universe)}) - "
                f"{strings.discord_timestamp(race['t'])}\n"
            )
        if text_id in disabled_text_ids:
            embed.set_footer(text="This text has been disabled")
        embeds.add_universe(embed, universe)

        return await ctx.send(embed=embed)

    await top_tens.update_results(text_id)
    top_10 = top_tens.get_top_n(text_id)

    for i, race in enumerate(top_10):
        username = race["username"]
        embed.description += (
            f"{strings.rank(i + 1)} {strings.escape_formatting(username)} - [{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['number'])}) - "
            f"{strings.discord_timestamp(race['timestamp'])}\n"
        )

    if not top_10:
        embed.description += "No scores found."

    await ctx.send(embed=embed)

    recent.text_id = text_id


async def setup(bot):
    await bot.add_cog(TextLeaderboard(bot))
