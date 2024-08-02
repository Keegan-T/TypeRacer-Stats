from discord import Embed
from discord.ext import commands

from database.bot_users import get_user
from database.users import get_text_bests
from utils import errors, colors, urls, strings, embeds

command = {
    "name": "compare",
    "aliases": ["vs"],
    "description": "Displays the top 10 races for each user sorted by text best WPM difference",
    "parameters": "[username_1] [username_2]",
    "usages": ["compare keegant poem"],
}


class Compare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def compare(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username1, username2 = result
        await run(ctx, user, username1, username2)


def get_args(user, args, info):
    params = "username username"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username1, username2):
    if username1 == username2:
        return await ctx.send(embed=same_username())

    if username2 == user["username"]:
        username2 = username1
        username1 = user["username"]

    universe = user["universe"]

    text_bests1 = get_text_bests(username1, race_stats=True, universe=universe)
    if not text_bests1:
        return await ctx.send(embed=errors.import_required(username1, universe))

    text_bests2 = get_text_bests(username2, race_stats=True, universe=universe)
    if not text_bests2:
        return await ctx.send(embed=errors.import_required(username2, universe))

    tb_dict1 = {text[0]: text[1:] for text in text_bests1}
    tb_dict2 = {text[0]: text[1:] for text in text_bests2}
    user1_better = 0
    user2_better = 0
    wpm_match = None

    comparison = {}

    for text_id in tb_dict1:
        if text_id in tb_dict2:
            score1 = tb_dict1[text_id]
            score2 = tb_dict2[text_id]
            gap = score1[0] - score2[0]
            if gap > 0:
                user1_better += 1
            elif gap < 0:
                user2_better += 1
            else:
                wpm_match = (score1, score2)
            comparison[text_id] = (tb_dict1[text_id], tb_dict2[text_id], gap)

    if not comparison:
        return await ctx.send(embed=no_common_texts(universe))

    comparison = sorted(comparison.items(), key=lambda x: x[1][2], reverse=True)

    stats1 = f"**{strings.escape_discord_format(username1)}** (+{user1_better:,} texts)\n"
    stats2 = f"**{strings.escape_discord_format(username2)}** (+{user2_better:,} texts)\n"

    for i, text in enumerate(comparison[:10]):
        gap = text[1][2]
        gap_string = f"({'+' * (gap >= 0)}{gap:,.2f} WPM)"
        stats1 += (
            f"{i + 1}. [{text[1][0][0]:,.2f}]({urls.replay(username1, text[1][0][1], universe)}) vs. "
            f"[{text[1][1][0]:,.2f}]({urls.replay(username2, text[1][1][1], universe)}) {gap_string}\n"
        )

    if wpm_match:
        stats1 += (
            f"\n:handshake: [{wpm_match[0][0]:,.2f}]({urls.replay(username1, wpm_match[0][1], universe)})"
            f" vs. [{wpm_match[1][0]:,.2f}]({urls.replay(username2, wpm_match[1][1], universe)})\n"
        )

    for i, text in enumerate(comparison[-10:][::-1]):
        gap = -text[1][2]
        gap_string = f"({'+' * (gap >= 0)}{gap:,.2f} WPM)"
        stats2 += (
            f"{i + 1}. [{text[1][1][0]:,.2f}]({urls.replay(username2, text[1][1][1], universe)}) vs. "
            f"[{text[1][0][0]:,.2f}]({urls.replay(username1, text[1][0][1], universe)}) {gap_string}\n"
        )

    description = stats1 + "\n" + stats2

    embed = Embed(
        title="Text Best Comparison",
        color=user["colors"]["embed"],
        description=description,
        url=urls.trdata_compare(username1, username2, universe),
    )
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


def same_username():
    return Embed(
        title="Same Username",
        description="Must input two unique usernames to compare",
        color=colors.error,
    )


def no_common_texts(universe):
    embed = Embed(
        title="No Data",
        description="Users do not have any texts in common",
        color=colors.error,
    )
    embeds.add_universe(embed, universe)

    return embed


async def setup(bot):
    await bot.add_cog(Compare(bot))
