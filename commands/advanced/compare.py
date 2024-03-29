from discord import Embed
from discord.ext import commands
import errors
import urls
import colors
import utils
from database.bot_users import get_user
from database.users import get_text_bests

info = {
    "name": "compare",
    "aliases": ["vs"],
    "description": "Displays the top 10 races for each user sorted by text best WPM difference",
    "parameters": "[username_1] [username_2]",
    "usages": ["compare keegant poem"],
    "import": True,
}


class Compare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def compare(self, ctx, *params):
        user = get_user(ctx)

        try:
            username1, username2 = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username1, username2)


async def get_params(ctx, user, params, command=info):
    username1 = None
    username2 = None

    if not params:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    if len(params) == 1:
        username1 = user["username"]
        username2 = params[0]

    if len(params) == 2:
        if params[0].lower() == "me":
            username1 = user["username"]
        else:
            username1 = params[0]

        if params[1].lower() == "me":
            username2 = user["username"]
        else:
            username2 = params[1]

    if not username1 or not username2:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    if username1 == username2:
        await ctx.send(embed=same_username())
        raise ValueError

    return username1.lower(), username2.lower()


async def run(ctx, user, username1, username2):
    text_bests1 = get_text_bests(username1, race_stats=True)
    if not text_bests1:
        return await ctx.send(embed=errors.import_required(username1))
    text_bests2 = get_text_bests(username2, race_stats=True)
    if not text_bests2:
        return await ctx.send(embed=errors.import_required(username2))

    tb_dict1 = {text[0]: text[1:] for text in text_bests1}
    tb_dict2 = {text[0]: text[1:] for text in text_bests2}

    comparison = {}

    for text_id in tb_dict1:
        if text_id in tb_dict2:
            score1 = tb_dict1[text_id]
            score2 = tb_dict2[text_id]
            gap = score1[0] - score2[0]
            comparison[text_id] = (tb_dict1[text_id], tb_dict2[text_id], gap)

    if not comparison:
        return await ctx.send(embed=no_common_texts())

    comparison = sorted(comparison.items(), key=lambda x: x[1][2], reverse=True)

    stats1 = f"**{username1}**\n"
    stats2 = f"**{username2}**\n"

    for i, text in enumerate(comparison[:10]):
        gap = text[1][2]
        gap_string = f"({'+' * (gap >= 0)}{gap:,.2f} WPM)"
        stats1 += (
            f"{i + 1}. [{text[1][0][0]:,.2f}]({urls.replay(username1, text[1][0][1])}) vs. "
            f"[{text[1][1][0]:,.2f}]({urls.replay(username2, text[1][1][1])}) {gap_string}\n"
        )

    for i, text in enumerate(comparison[-10:][::-1]):
        gap = -text[1][2]
        gap_string = f"({'+' * (gap >= 0)}{gap:,.2f} WPM)"
        stats2 += (
            f"{i + 1}. [{text[1][1][0]:,.2f}]({urls.replay(username2, text[1][1][1])}) vs. "
            f"[{text[1][0][0]:,.2f}]({urls.replay(username1, text[1][0][1])}) {gap_string}\n"
        )

    description = stats1 + "\n" + stats2

    embed = Embed(
        title="Text Best Comparison",
        color=user["colors"]["embed"],
        description=description,
        url=urls.trdata_compare(username1, username2),
    )

    await ctx.send(embed=embed)


def same_username():
    return Embed(
        title="Same Username",
        description="Must input two unique usernames to compare",
        color=colors.error,
    )


def no_common_texts():
    return Embed(
        title="No Data",
        description="Users do not have any texts in common",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Compare(bot))
