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

info = {
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
}


class MissingTens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def missingtens(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, sort = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, sort)


async def get_params(ctx, user, params, command=info):
    username = user["username"]
    sort = "best"

    if params and params[0].lower() != "me":
        username = params[0]

    if not username:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    if len(params) > 1:
        if params[1] in ["random", "rand", "r"]:
            sort = "random"
        elif params[1] == "worst":
            sort = "worst"

    return username.lower(), sort

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
        missing_texts.sort(key=lambda x: x["difference"])
    elif sort == "worst":
        missing_texts.sort(key=lambda x: -x["difference"])
    elif sort == "random":
        shuffle(missing_texts)

    embed = Embed(
        title="Missing Top Tens",
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
