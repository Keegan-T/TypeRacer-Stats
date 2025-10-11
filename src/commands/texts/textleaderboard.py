from discord.ext import commands

import api.texts as texts_api
import database.bot.recent_text_ids as recent
import database.main.text_results as top_tens
import database.main.texts as texts
from api.core import date_to_timestamp
from database.bot.users import get_user
from utils import errors, urls, strings, embeds
from utils.embeds import Page, Message

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
        args, user = strings.set_wpm_metric(args, user)

        result = get_args(user, args, command, ctx.channel.id)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        text_id = result
        await run(ctx, user, text_id)


def get_args(user, args, info, channel_id):
    params = "text_id"

    result = strings.parse_command(user, params, args, info, channel_id)
    if embeds.is_embed(result):
        return result

    return result[0]


async def run(ctx, user, text_id):
    universe = user["universe"]
    text = texts.get_text(text_id, universe)
    if not text:
        return await ctx.send(embed=errors.unknown_text(universe))
    wpm_metric = user["settings"]["wpm"]

    full_quote = text["quote"]
    characters = len(full_quote)
    words = len(full_quote.split(" "))
    quote = strings.truncate_clean(full_quote, 1000)
    page = Page(
        title=f"Text #{text_id}",
        description=(
            f'{words:,} words - {characters:,} characters - '
            f'[Ghost]({text["ghost"]})\n"{quote}"\n\n**Top 10**\n'
        ),
        color=user["colors"]["embed"],
    )
    url = urls.trdata_text(text_id, universe)

    text_id = int(text_id)
    disabled_text_ids = texts.get_disabled_text_ids()

    if universe != "play":
        top_10 = texts_api.get_trdata_top_10(text_id, universe)

    else:
        if text_id in disabled_text_ids:
            top_10 = await texts_api.get_top_results(text_id)
            for i, race in enumerate(top_10):
                username = race["user"]
                page.description += (
                    f"{strings.rank(i + 1)} {strings.escape_formatting(username)} - [{race['wpm']:,.2f} WPM]"
                    f"({urls.replay(username, race['rn'], universe)}) - "
                    f"{strings.discord_timestamp(date_to_timestamp(race['t']))}\n"
                )
            page.footer = "This text has been disabled"
            message = Message(ctx, user, page, url=url)
            return await message.send()

        await top_tens.update_results(text_id)
        top_10 = top_tens.get_top_n(text_id, wpm=wpm_metric)

    for i, race in enumerate(top_10):
        username = race["username"]
        accuracy_string = ""
        if race["accuracy"]:
            accuracy_string = f" ({race['accuracy']:.0%})"
        page.description += (
            f"{strings.rank(i + 1)} {strings.escape_formatting(username)} - [{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['number'])}){accuracy_string} - "
            f"{strings.discord_timestamp(race['timestamp'])}\n"
        )

    if not top_10:
        page.description += "No scores found."

    message = Message(
        ctx, user, page,
        url=url,
        wpm_metric=wpm_metric,
        universe=user["universe"],
    )

    await message.send()

    recent.update_recent(ctx.channel.id, text_id)


async def setup(bot):
    await bot.add_cog(TextLeaderboard(bot))
