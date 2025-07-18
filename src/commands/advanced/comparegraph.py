from discord.ext import commands

from commands.advanced.compare import get_args
from database.main import users
from database.bot.users import get_user
from database.main.users import get_text_bests
from graphs import compare_graph
from utils import errors, urls, strings, dates
from utils.embeds import Page, Field, Message, is_embed

command = {
    "name": "comparegraph",
    "aliases": ["flaneur", "cg", "vsg", "vg"],
    "description": "Displays histograms comparing two user's text best WPM differences",
    "parameters": "[username_1] [username_2]",
    "usages": ["comparegraph keegant hospitalforsouls2"],
}


class CompareGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def comparegraph(self, ctx, *args):
        user = get_user(ctx)
        args, user = dates.set_command_date_range(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username1, username2 = result
        await run(ctx, user, username1, username2)


async def run(ctx, user, username1, username2):
    if username1 == username2:
        return await ctx.send(embed=errors.same_username())

    if username2 == user["username"]:
        username2 = username1
        username1 = user["username"]

    universe = user["universe"]
    era_string = strings.get_era_string(user)

    if era_string:
        text_bests1 = await users.get_text_bests_time_travel(username1, universe, user)
        text_bests2 = await users.get_text_bests_time_travel(username2, universe, user)

    else:
        text_bests1 = get_text_bests(username1, race_stats=True, universe=universe)
        if not text_bests1:
            return await ctx.send(embed=errors.import_required(username1, universe))

        text_bests2 = get_text_bests(username2, race_stats=True, universe=universe)
        if not text_bests2:
            return await ctx.send(embed=errors.import_required(username2, universe))

    tb_dict = {text[0]: text[1] for text in text_bests1}

    max_gap1 = (0, 0, 0)
    max_gap2 = (0, 0, 0)
    min_gap1 = (0, float('inf'), 0)
    min_gap2 = (0, float('inf'), 0)
    wpm_match = None

    data1, data2 = [], []

    for text in text_bests2:
        if (wpm := tb_dict.get(text[0], -1)) > 0:
            difference = text[1] - wpm
            if difference == 0 and (not wpm_match or wpm_match and wpm_match[1] < text[1]):
                wpm_match = (text[0], text[1])
            elif difference < 0:
                data1.append(-difference)
                if -difference > max_gap1[1] - max_gap1[2]:
                    max_gap1 = (text[0], wpm, text[1])
                if -difference < min_gap1[1] - min_gap1[2]:
                    min_gap1 = (text[0], wpm, text[1])
            else:
                data2.append(difference)
                if difference > max_gap2[1] - max_gap2[2]:
                    max_gap2 = (text[0], text[1], wpm)
                if difference < min_gap2[1] - min_gap2[2]:
                    min_gap2 = (text[0], text[1], wpm)

    if not data1:
        if not data2:
            return await ctx.send(embed=errors.no_common_texts(universe), content=era_string)
        data1, data2 = data2, data1
        username1, username2 = username2, username1
        max_gap1, max_gap2 = max_gap2, max_gap1
        min_gap1, min_gap2 = min_gap2, min_gap1

    same_text = ""
    if wpm_match:
        same_text = (
            f"Text [#{wpm_match[0]}]({urls.trdata_text(wpm_match[0], universe)}&highlight={username1}) - "
            f"{wpm_match[1]:,.2f} WPM \U0001F91D"
        )

    gap2 = (
        f"**Biggest Gap:** +{max_gap2[1] - max_gap2[2]:,.2f} WPM \n"
        f"({max_gap2[1]} WPM vs. {max_gap2[2]} WPM)\n"
        f"{same_text}"
    )

    description = ""
    if not data2:
        description = "\U0001F3C6 **TOTAL DOMINATION** \U0001F3C6"
        gap2 = (
            f"**Closest:** -{min_gap1[1] - min_gap1[2]:,.2f} WPM \n"
            f"({min_gap1[2]} WPM vs. {min_gap1[1]} WPM)\n"
            f"{same_text}"
        )

    texts1 = len(data1)
    texts2 = len(data2)
    gain1 = sum(data1)
    gain2 = sum(data2)
    average_gain1 = gain1 / texts1
    if texts2 == 0:
        average_gain2 = 0
    else:
        average_gain2 = gain2 / texts2

    stats1 = (
        f"**Texts:** +{texts1:,}\n"
        f"**Gain:** +{gain1:,.2f} WPM\n"
        f"**Average Gain:** +{average_gain1:,.2f} WPM\n"
        f"**Biggest Gap:** +{max_gap1[1] - max_gap1[2]:,.2f} WPM\n"
        f"({max_gap1[1]} WPM vs. {max_gap1[2]} WPM)\n"
        f"{same_text}"
    )

    stats2 = (
        f"**Texts:** +{texts2:,}\n"
        f"**Gain:** +{gain2:,.2f} WPM\n"
        f"**Average Gain:** +{average_gain2:,.2f} WPM\n"
        f"{gap2}"
    )

    page = Page(
        description=description,
        fields=[
            Field(strings.escape_formatting(username1), stats1),
            Field(strings.escape_formatting(username2), stats2),
        ],
        render=lambda: compare_graph.render(user, (username1, data1), (username2, data2), universe),
    )

    message = Message(
        ctx, user, page,
        title="Text Best Comparison",
        url=urls.trdata_compare(username1, username2),
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(CompareGraph(bot))
