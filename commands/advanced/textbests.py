from discord import Embed
from discord.ext import commands
import math

import urls
import utils
import errors
from database.bot_users import get_user
import database.users as users
import database.texts as texts
from config import prefix

info = {
    "name": "textbests",
    "aliases": ["tb"],
    "description": "Displays a user's text best average and their best quotes\n"
                   "Providing `n` will display the average of the user's top n texts\n"
                   f"`{prefix}textbests [username] worst` will show the user's worst quotes",
    "parameters": "[username] <n>",
    "usages": [
        "textbests keegant",
        "textbests keegant worst",
        "textbests charlieog 100",
    ],
}


class TextBests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def textbests(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, n, worst = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, n, worst)


async def get_params(ctx, user, params, command=info):
    username = user["username"]
    worst = False
    n = 100_000

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        if params[1] in ["worst", "w"]:
            worst = True
        else:
            try:
                n = utils.parse_value_string(params[1])
            except ValueError:
                await ctx.send(embed=errors.invalid_number_format())
                raise ValueError

    if n < 1:
        await ctx.send(embed=errors.greater_than(0))
        raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    return username.lower(), n, worst


async def run(ctx, user, username, n, worst):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    text_list = texts.get_texts(as_dictionary=True)
    text_bests = users.get_text_bests(username, race_stats=True)
    if worst: text_bests.reverse()
    text_bests = text_bests[:n]
    texts_typed = len(text_bests)
    total_text_wpm = sum(text["wpm"] for text in text_bests)
    average = total_text_wpm / texts_typed
    next_milestone = 5 * math.ceil(average / 5)
    required_wpm_gain = texts_typed * next_milestone - total_text_wpm

    description = (
        f"**Text Best Average:** {average:,.2f} WPM\n"
        f"**Texts Typed:** {texts_typed:,}\n"
        f"**Text WPM Total:** {total_text_wpm:,.0f} WPM\n"
        f"**Gain Until {next_milestone} Average:** {required_wpm_gain:,.0f} WPM\n"
    )

    limit = 10
    scores = ""

    for text in text_bests[:limit]:
        text_id = text["text_id"]
        quote = utils.truncate_clean(text_list[text_id]["quote"], 60)
        scores += (
            f"[{text['wpm']:,.2f} WPM]({urls.trdata_text(text_id)}) - "
            f"Race #{text['number']:,} - "
            f"[Text #{text_id}]({urls.trdata_text(text_id)}) - "
            f'{utils.discord_timestamp(text["timestamp"])}\n"{quote}"\n\n'
        )

    title = f"Text Bests"
    if n < stats["texts_typed"]:
        title += f" (Top {n:,} Texts)"
    elif worst:
        title += f" (Worst Texts)"
    embed = Embed(
        title=title,
        description=f"{description}\n{scores}",
        color=user["colors"]["embed"],
    )

    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TextBests(bot))
