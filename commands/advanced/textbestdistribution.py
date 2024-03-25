from discord import Embed
from discord.ext import commands
import math
import utils
import errors
from database.bot_users import get_user
from commands.basic.stats import get_params
import database.users as users
import database.texts as texts

info = {
    "name": "textbestdistribution",
    "aliases": ["tbd", "bd"],
    "description": "Displays a WPM distribution of a user's text bests",
    "parameters": "[username]",
    "usages": ["textbestdistribution keegant"],
    "import": True,
}


class TextBestDistribution(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def textbestdistribution(self, ctx, *params):
        user = get_user(ctx)

        try:
            username = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username)


async def run(ctx, user, username):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    text_list = texts.get_texts(include_disabled=False)
    text_bests = users.get_text_bests(username)

    top_bracket = min(300, int(10 * (math.floor(text_bests[0]["wpm"] / 10))))
    bottom_bracket = int(10 * (math.floor(text_bests[-1]["wpm"] / 10)))
    brackets = []
    spacing = [len(str(top_bracket)), 4, 6, 4]

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

        brackets.append((wpm, over, completion, left))

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
        f"{'Left':>{spacing[3]}}\n"
    )

    for bracket in brackets:
        bracket_str = (
            f"\u001B[2;34m{bracket[0]:<{spacing[0]}} WPM+\u001B[0m | "
            f"\u001B[2;34m{bracket[1]:>{spacing[1]}}\u001B[0m | "
            f"\u001B[2;34m{bracket[2]:>{spacing[2]}}%\u001B[0m | "
            f"\u001B[2;34m{bracket[3]:>{spacing[3]}}\u001B[0m"
        )
        breakdown += f"{bracket_str}\n"

    description += f"\n\n**Distribution:**\n```ansi\n{breakdown}```"

    embed = Embed(
        title=f"Text Best Distribution",
        description=description,
        color=user["colors"]["embed"],
    )

    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TextBestDistribution(bot))
