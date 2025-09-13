from bisect import bisect_right

from discord.ext import commands

import database.main.texts as texts
import database.main.users as users
from commands.stats.stats import get_args
from database.bot.users import get_user
from database.main import races
from utils import errors, strings, urls
from utils.embeds import Page, Message, is_embed

command = {
    "name": "timestypeddistribution",
    "aliases": ["ttd"],
    "description": "Displays a distribution of a user's texts by times typed",
    "parameters": "[username]",
    "usages": ["timestypeddistribution charlieog"],
}


class TimesTypedDistribution(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def timestypeddistribution(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if is_embed(result):
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

    race_list = await races.get_races(
        username, columns=["text_id"], universe=universe,
        start_date=user["start_date"], end_date=user["end_date"],
    )
    text_list = texts.get_texts(get_disabled=False, universe=universe)
    disabled_ids = texts.get_disabled_text_ids()

    times_typed = {text["text_id"]: 0 for text in text_list}
    for race in race_list:
        text_id = race["text_id"]
        if text_id not in disabled_ids:
            times_typed[text_id] += 1

    counts = list(times_typed.values())
    counts.sort()
    max_text_id = next(text_id for text_id, count in times_typed.items() if count == counts[-1])

    brackets = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, float("inf")]
    min_typed = min(counts)
    max_typed = max(counts)
    total_texts = len(text_list)

    while max_typed < brackets[-1]:
        brackets.pop()
    while min_typed > brackets[0]:
        brackets = brackets[1:]

    if min_typed >= 10:
        brackets = brackets[:1] + [brackets[0] + 1] + brackets[1:]
    if max_typed >= 10:
        brackets.append(max_typed)

    at_counts = [0] * len(brackets)
    for count in counts:
        index = bisect_right(brackets, count) - 1
        at_counts[index] += 1

    over_counts = [0] * len(brackets)
    cumulative = 0
    for i in reversed(range(len(brackets))):
        cumulative += at_counts[i]
        over_counts[i] = cumulative

    if brackets[0] == 0:
        brackets.pop(0)
        over_counts.pop(0)

    spacing = [len(str(brackets[-1])), 6, 6, 4]
    seen = set()
    bracket_rows = []

    for i in reversed(range(len(brackets))):
        over = over_counts[i]
        if over in seen:
            continue
        seen.add(over)

        bracket = brackets[i]
        bracket_str = f"{bracket:,}+ times"
        over_str = f"{over:,}"
        left = f"{total_texts - over:,}"
        done_percent = f"{over / total_texts:.2%}"

        spacing[0] = max(spacing[0], len(bracket_str))
        spacing[1] = max(spacing[1], len(over_str))
        spacing[2] = max(spacing[2], len(done_percent))
        spacing[3] = max(spacing[3], len(left))

        bracket_rows.append((bracket_str, over_str, done_percent, left))
    bracket_rows.reverse()

    texts_typed = over_counts[0]
    race_count = len(race_list)
    description = (
        f"**Texts Typed:** {texts_typed:,} of {total_texts:,} ({texts_typed / total_texts:.2%})\n"
        f"**Races:** {race_count:,}\n"
        f"**Avg. Times Per Text:** {race_count / texts_typed:.2f}\n"
        f"**Most Typed Text:** [#{max_text_id}]({urls.trdata_text(max_text_id, universe)})\n"
    )

    breakdown = (
        f"{'Bracket':<{spacing[0]}} | "
        f"{'Over':>{spacing[1]}} | "
        f"{'Done':>{spacing[2]}} | "
        f"{'Left':>{spacing[3]}}\n"
    )

    for row in bracket_rows:
        bracket, over, done, left = row
        breakdown += (
            f"{bracket:<{spacing[0]}} | "
            f"{over:>{spacing[1]}} | "
            f"{done:>{spacing[2]}} | "
            f"{left:>{spacing[3]}}\n"
        )

    description += f"\n**Distribution:**\n```text\n{breakdown}```"

    page = Page(
        title=f"Times Typed Distribution",
        description=description,
    )

    message = Message(
        ctx, user, page,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(TimesTypedDistribution(bot))
