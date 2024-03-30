from discord import Embed
from discord.ext import commands
import utils
import errors
import urls
from database.bot_users import get_user
import database.texts as texts
import api.texts as texts_api
import commands.recent as recent
import database.text_results as top_tens

info = {
    "name": "textleaderboard",
    "aliases": ["tl", "10"],
    "description": "Displays the top 10 leaderboard for a text",
    "defaults": {
        "text_id": "the most recently viewed text ID"
    },
    "parameters": "<text_id>",
    "usages": ["textleaderboard 3810446"],
    "import": False,
}


class TextLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def textleaderboard(self, ctx, *params):
        user = get_user(ctx)

        if params:
            if params[0] == "^":
                text_id = recent.text_id
            else:
                text_id = params[0]
        else:
            text_id = recent.text_id

        await run(ctx, user, text_id)


async def run(ctx, user, text_id):
    text = texts.get_text(text_id)
    if not text:
        return await ctx.send(embed=errors.unknown_text())

    embed = Embed(
        title=f"Text #{text_id}",
        url=urls.trdata_text(text_id),
        color=user["colors"]["embed"],
    )

    full_quote = text["quote"]
    characters = len(full_quote)
    words = len(full_quote.split(" "))
    quote = utils.truncate_clean(full_quote, 1000)
    embed.description = (
        f'{words:,} words - {characters:,} characters - '
        f'[Ghost]({text["ghost"]})\n"{quote}"\n\n**Top 10**\n'
    )

    text_id = int(text_id)
    disabled_text_ids = texts.get_disabled_text_ids()

    if text_id in disabled_text_ids:
        top_10 = await texts_api.get_top_10(text_id)
        for i, score in enumerate(top_10):
            race, user = score
            username = user["id"][3:]
            embed.description += (
                f"{utils.rank(i + 1)} {utils.escape_discord_format(username)} - [{race['wpm']:,.2f} WPM]"
                f"({urls.replay(username, race['gn'])}) - "
                f"{utils.discord_timestamp(race['t'])}\n"
            )
        embed.set_footer(text="This text has been disabled")

        return await ctx.send(embed=embed)

    await top_tens.update_results(text_id)
    top_10 = top_tens.get_top_10(text_id)

    for i, race in enumerate(top_10):
        username = race["username"]
        embed.description += (
            f"{utils.rank(i + 1)} {utils.escape_discord_format(username)} - [{race['wpm']:,.2f} WPM]"
            f"({urls.replay(race['username'], race['number'])}) - "
            f"{utils.discord_timestamp(race['timestamp'])}\n"
        )

    if not top_10:
        embed.description += "No scores found."

    await ctx.send(embed=embed)

    recent.text_id = text_id


async def setup(bot):
    await bot.add_cog(TextLeaderboard(bot))
