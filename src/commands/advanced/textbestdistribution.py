import math

from discord import Embed
from discord.ext import commands

import database.texts as texts
import database.users as users
from commands.basic.stats import get_args
from database.bot_users import get_user
from utils import errors, embeds, strings

command = {
    "name": "textbestdistribution",
    "aliases": ["tbd", "bd"],
    "description": "Displays a WPM distribution of a user's text bests",
    "parameters": "[username]",
    "usages": ["textbestdistribution keegant"],
}


class TextBestDistribution(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def textbestdistribution(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username)


async def run(ctx, user, username):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)
    if era_string:
        stats = await users.time_travel_stats(stats, user)

    text_list = texts.get_texts(include_disabled=False, universe=universe)

    if era_string:
        text_bests = await users.get_text_bests_time_travel(username, universe, user)
    else:
        text_bests = users.get_text_bests(username, universe=universe)

    if len(text_bests) == 0:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

    top_bracket = int(10 * (math.floor(text_bests[0]["wpm"] / 10)))
    bottom_bracket = int(10 * (math.floor(text_bests[-1]["wpm"] / 10)))
    brackets = []
    spacing = [len(str(top_bracket)), 4, 6, 4]

    previous_over = 0
    for wpm in range(bottom_bracket, top_bracket + 1, 10):
        over = len([text for text in text_bests if text["wpm"] >= wpm])
        completion = f"{(over / len(text_bests)) * 100:,.2f}"
        left = f"{len(text_bests) - over:,}"
        over = f"{over:,}"
        wpm = f"{wpm}"

        if len(over) > spacing[1]:
            spacing[1] = len(over)
        if len(left) > spacing[3]:
            spacing[3] = len(left)

        if over == previous_over:
            brackets.pop()
        brackets.append((wpm, over, completion, left))
        previous_over = over

    average = stats["text_best_average"]
    texts_typed = stats["texts_typed"]
    text_count = len(text_list)
    texts_typed_percentage = (texts_typed / text_count) * 100
    bold = "**" if texts_typed_percentage == 100 else ""
    total_text_wpm = stats["text_wpm_total"]
    next_milestone = 5 * math.ceil(average / 5)
    required_wpm_gain = texts_typed * next_milestone - total_text_wpm

    description = (
        f"**Text Best Average:** {average:,.2f} WPM\n"
        f"**Texts Typed:** {texts_typed:,} of {text_count:,} "
        f"({bold}{texts_typed_percentage:.2f}%{bold})\n"
        f"**Text WPM Total:** {total_text_wpm:,.0f} WPM\n"
        f"**Gain Until {next_milestone} Average:** {required_wpm_gain:,.0f} WPM"
    )

    breakdown = (
        f"{'Bracket':<{spacing[0] + 5}} | "
        f"{'Over':>{spacing[1]}} | "
        f"{'Done':>{spacing[2] + 1}} | "
        f"{'Left':>{spacing[3]}}\t\t\n"
    )

    for bracket in brackets:
        bracket_str = (
            f"{bracket[0]:<{spacing[0]}} WPM+ | "
            f"{bracket[1]:>{spacing[1]}} | "
            f"{bracket[2]:>{spacing[2]}}% | "
            f"{bracket[3]:>{spacing[3]}}"
        )
        breakdown += f"{bracket_str}\n"

    description += f"\n\n**Distribution:**\n```\n{breakdown}```"

    embed = Embed(
        title=f"Text Best Distribution",
        description=description,
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)


async def setup(bot):
    await bot.add_cog(TextBestDistribution(bot))
