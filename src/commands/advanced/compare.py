from random import shuffle

from discord.ext import commands

from config import prefix
from database.main import users
from database.bot.users import get_user
from database.main.users import get_text_bests
from utils import errors, urls, strings, dates
from utils.embeds import Page, Message, is_embed

command = {
    "name": "compare",
    "aliases": ["vs", "v", "vr", "vc", "vn", "vo"],
    "description": "Displays the top 10 races for each user sorted by text best WPM difference\n"
                   f"Use `{prefix}vc` to view closest results"
                   f"Use `{prefix}vr` to randomize the results"
                   f"Use `{prefix}vn` to view newest results"
                   f"Use `{prefix}vo` to view oldest results",
    "parameters": "[username_1] [username_2]",
    "usages": ["compare keegant poem"],
}


class Compare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def compare(self, ctx, *args):
        user = get_user(ctx)
        args, user = dates.set_command_date_range(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username1, username2 = result
        await run(ctx, user, username1, username2)


def get_args(user, args, info):
    params = "username username"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username1, username2):
    if username1 == username2:
        return await ctx.send(embed=errors.same_username())

    if username2 == user["username"]:
        username2 = username1
        username1 = user["username"]

    universe = user["universe"]

    era_string = strings.get_era_string(user)
    if era_string:
        text_bests1 = await users.get_text_bests_time_travel(username1, universe, user, race_stats=True)
        text_bests2 = await users.get_text_bests_time_travel(username2, universe, user, race_stats=True)

    else:
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
                if not wpm_match or wpm_match and wpm_match[0][0] < score1[0]:
                    wpm_match = (score1, score2)
            comparison[text_id] = (tb_dict1[text_id], tb_dict2[text_id], gap)

    if not comparison:
        return await ctx.send(embed=errors.no_common_texts(universe), content=era_string)

    comparison = sorted(comparison.items(), key=lambda x: x[1][2], reverse=True)
    positive = [x for x in comparison if x[1][2] >= 0]
    negative = [x for x in comparison if x[1][2] < 0]
    positive.reverse()
    negative.reverse()
    comparison_close = positive + negative
    shuffle(positive)
    shuffle(negative)
    comparison_random = positive + negative
    positive.sort(key=lambda x: -x[1][0][2])
    negative.sort(key=lambda x: x[1][1][2])
    comparison_new = positive + negative
    positive.reverse()
    negative.reverse()
    comparison_old = positive + negative

    def wpm_string(gap, score1, score2, username1, username2):
        wpm1, race_number1 = score1[:2]
        wpm2, race_number2 = score2[:2]
        gap_string = f"({'+' * (gap >= 0)}{gap:,.2f} WPM)"
        return (
            f"[{wpm1:,.2f}]({urls.replay(username1, race_number1, universe)}) vs. "
            f"[{wpm2:,.2f}]({urls.replay(username2, race_number2, universe)}) {gap_string}\n"
        )

    def formatter(comparison):
        stats1 = f"**{strings.escape_formatting(username1)}** (+{user1_better:,} texts)\n"
        stats2 = f"**{strings.escape_formatting(username2)}** (+{user2_better:,} texts)\n"

        for i, (text_id, data) in enumerate(comparison[:10]):
            score1, score2, gap = data
            stats1 += f"{i + 1}. " + wpm_string(gap, score1, score2, username1, username2)

        if wpm_match:
            score1, score2 = wpm_match
            wpm1, race_number1 = score1[:2]
            wpm2, race_number2 = score2[:2]
            stats1 += (
                f"\n:handshake: [{wpm1:,.2f}]({urls.replay(username1, race_number1, universe)})"
                f" vs. [{wpm2:,.2f}]({urls.replay(username2, race_number2, universe)})\n"
            )

        for i, (text_id, data) in enumerate(comparison[::-1][:10]):
            score1, score2, gap = data
            stats2 += f"{i + 1}. " + wpm_string(-gap, score2, score1, username2, username1)

        return stats1 + "\n" + stats2

    description = formatter(comparison)
    description_random = formatter(comparison_random)
    description_close = formatter(comparison_close)
    description_new = formatter(comparison_new)
    description_old = formatter(comparison_old)
    title = "Text Best Comparison"

    pages = [
        Page(title, description, button_name="Farthest"),
        Page(title + " (Closest)", description_close, button_name="Closest", default=ctx.invoked_with == "vc"),
        Page(title + " (Randomized)", description_random, button_name="Random", default=ctx.invoked_with == "vr"),
        Page(title + " (Newest)", description_new, button_name="Newest", default=ctx.invoked_with == "vn"),
        Page(title + " (Oldest)", description_old, button_name="Oldest", default=ctx.invoked_with == "vo"),
    ]

    message = Message(
        ctx=ctx,
        pages=pages,
        user=user,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Compare(bot))
