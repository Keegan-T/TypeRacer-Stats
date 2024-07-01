from discord import Embed
from discord.ext import commands
import errors
import urls
import utils
from config import prefix
from database.bot_users import get_user
import database.texts as texts
import database.users as users
import database.text_results as text_results
from random import shuffle

sorts = ["best", "worst", "random"]
command = {
    "name": "missingtens",
    "aliases": ["mt", "josh"],
    "description": "Displays a list of texts a user has typed but not ranked within the top 10",
    "parameters": "[username] <sort>",
    "defaults": {
        "sort": "best",
    },
    "usages": [
        "missingtens joshua728",
        "missingtens helloimnotgood1 worst",
        "missingtens poke1 random"
    ],
    "multiverse": False,
}


class MissingTens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def missingtens(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, sort = get_args(user, args, command)
        await run(ctx, user, username, sort)


def get_args(user, args, info):
    params = f"username sort:{'|'.join(sorts)}"

    return utils.parse_command(user, params, args, info)


async def run(ctx, user, username, sort):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    text_list = texts.get_texts(as_dictionary=True)
    text_bests = users.get_text_bests(username)
    top_10s = text_results.get_top_10s()
    missing_texts = []

    for text in text_bests:
        text_id = text[0]
        wpm = text[1]
        missing = True
        tenth_wpm = 0
        top_10 = top_10s[text_id]
        for score in top_10:
            if score["username"] == username:
                missing = False
            tenth_wpm = score["wpm"]
        if missing:
            difference = tenth_wpm - wpm
            if difference >= 0:
                missing_texts.append({
                    "text_id": text_id,
                    "wpm": wpm,
                    "difference": difference,
                })

    if sort == "best":
        sort_title = "Closest"
        missing_texts.sort(key=lambda x: x["difference"])
    elif sort == "worst":
        sort_title = "Farthest"
        missing_texts.sort(key=lambda x: -x["difference"])
    elif sort == "random":
        sort_title = "Randomized"
        shuffle(missing_texts)

    embed = Embed(
        title=f"Missing Top Tens ({sort_title})",
        color=user["colors"]["embed"],
    )

    if not missing_texts:
        description = "User ranks in every top 10 for texts they have typed!"

    else:
        description = ""
        for text in missing_texts[:10]:
            text_id = text["text_id"]
            wpm = text["wpm"]
            difference = text["difference"]
            description += (
                f"[Text #{text_id}]({urls.trdata_text(text_id)}) - "
                f"{wpm:,.2f} WPM ({difference:,.2f} WPM from 10th) - "
                f"[Ghost]({text_list[text_id]['ghost']})\n"
                f'"{utils.truncate_clean(text_list[text_id]["quote"], 60)}"\n\n'
            )
            if difference < 0:
                embed.set_footer(text="Negative differences mean that a higher score exists on an alternate account")

    embed.description = description
    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MissingTens(bot))
