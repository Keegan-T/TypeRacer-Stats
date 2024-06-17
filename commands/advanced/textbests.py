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

command = {
    "name": "textbests",
    "aliases": ["tb"],
    "description": "Displays a user's text best average and their best texts\n"
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

    @commands.command(aliases=command["aliases"])
    async def textbests(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, n, worst = result
        await run(ctx, user, username, n, worst)


def get_args(user, args, info):
    worst = False
    params = "username int:99999"

    result = utils.parse_command(user, params, args, info)
    if utils.is_embed(result):
        if len(args) > 1 and args[1] in ["worst", "w"]:
            username = args[0]
            if user["username"] and username == "me":
                username = user["username"]
            n = 99999
            worst = True
        else:
            return result
    else:
        username, n = result

    return username, n, worst


async def run(ctx, user, username, n, worst):
    if n < 1:
        return await ctx.send(embed=errors.greater_than(0))

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
            f"[{text['wpm']:,.2f} WPM]({urls.replay(username, text['number'])}) - "
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
