from discord import Embed, File
from discord.ext import commands
import graphs
import utils
import errors
import math
from database.bot_users import get_user
import database.users as users
import database.races as races
import database.texts as texts

categories = ["races", "time", "texts"]
command = {
    "name": "textbestsgraph",
    "aliases": ["tbg"],
    "description": "Displays a graph of a user's text best average over time",
    "parameters": "[username] <category>",
    "defaults": {
        "category": "races"
    },
    "usages": [
        "textbestsgraph keegant time",
        "textbestsgraph keegant races",
        "textbestsgraph keegant texts",
    ],
}


class TextBestsGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textbestsgraph(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, category = result
        await run(ctx, user, username, category)

def get_args(user, args, info):
    params = f"username category:{'|'.join(categories)}"

    return utils.parse_command(user, params, args, info)

async def run(ctx, user, username, category):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    x = []
    y = []
    text_ids = {}
    disabled_text_ids = texts.get_disabled_text_ids()
    wpm_total = 0
    wpm_count = 0

    columns = ["number", "wpm", "text_id", "timestamp"]
    race_list = await races.get_races(username, columns=columns, universe=universe)
    race_list.sort(key=lambda r: r[0])

    for race in race_list:
        if race[2] in disabled_text_ids:
            continue

        appendage = len(x)
        if category == "races":
            appendage = race[0]
        elif category == "time":
            appendage = race[3]

        if text_ids.get(race[2], False):
            if race[1] > text_ids[race[2]]:
                x.append(appendage)
                wpm_total += race[1] - text_ids[race[2]]
                text_ids.update({race[2]: race[1]})
                y.append(wpm_total / wpm_count)
        else:
            x.append(appendage)
            text_ids.update({race[2]: race[1]})
            wpm_total += race[1]
            wpm_count += 1
            y.append(wpm_total / wpm_count)

    average = y[-1]
    texts_typed = len(text_ids)
    next_milestone = 5 * math.ceil(average / 5)
    required_wpm_gain = texts_typed * next_milestone - wpm_total

    description = (
        f"**Text Best Average:** {average:,.2f} WPM\n"
        f"**Texts Typed:** {texts_typed:,}\n"
        f"**Text WPM Total:** {wpm_total:,.0f} WPM\n"
        f"**Gain Until {next_milestone} Average:** {required_wpm_gain:,.0f} WPM"
    )

    embed = Embed(
        title=f"Text Best Progression",
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats, universe)
    utils.add_universe(embed, universe)

    file_name = f"text_bests_over_{category}_{username}.png"
    graphs.text_bests(user, username, x, y, category, file_name, universe)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    utils.remove_file(file_name)


async def setup(bot):
    await bot.add_cog(TextBestsGraph(bot))
