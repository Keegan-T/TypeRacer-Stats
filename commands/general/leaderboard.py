from discord import Embed
from discord.ext import commands
from src import urls, errors, utils
from src.config import prefix
from database.bot_users import get_user
import database.users as users
import database.texts as texts
import database.text_results as top_tens
import database.competition_results as competition_results

categories = ["races", "points", "awards", "textbests", "textstyped", "toptens",
              "textrepeats", "totaltextwpm", "wpm", "racetime", "characters"]
info = {
    "name": "leaderboard",
    "aliases": ["lb"],
    "description": "Displays the top 10 users in a category\n"
                   f"`{prefix}leaderboard [n]` will show top n appearances",
    "parameters": "[category]",
    "usages": [f"leaderboard {category}" for category in categories],
    "import": False,
}


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def leaderboard(self, ctx, *params):
        user = get_user(ctx)
        text_id = None

        if not params:
            return await ctx.send(embed=errors.missing_param(info))

        category_string = params[0]

        if category_string.isnumeric() and 1 <= int(category_string) <= 10:
            category = category_string
        else:
            category = utils.get_category(categories, category_string)
            if not category:
                return await ctx.send(embed=errors.invalid_option("category", categories))

        if len(params) > 1:
            text_id = params[1]

        await run(ctx, user, category, text_id)


async def run(ctx, user, category, text_id=None):
    limit = 10
    leaders = []
    leaderboard_string = ""

    embed = Embed(color=user["colors"]["embed"])

    if category == "races":
        title = "Races"
        leaderboard = users.get_most("races", limit)
        for leader in leaderboard:
            leaders.append(f"{leader['races']:,}")

    elif category == "points":
        title = "Points"
        leaderboard = users.get_most_total_points(limit)
        for leader in leaderboard:
            leaders.append(f"{leader['points_total']:,.0f}")

    elif category == "awards":
        title = "Awards"
        leaderboard = users.get_most_awards(limit)
        for leader in leaderboard:
            first = leader["awards_first"]
            second = leader["awards_second"]
            third = leader["awards_third"]
            total = first + second + third
            leaders.append(f"{total:,} - :first_place: x{first:,} :second_place: x{second:,} :third_place: x{third:,}")
        comp_count = competition_results.get_count()
        embed.set_footer(text=f"Across {comp_count:,} competitions")

    elif category == "textbests":
        title = "Text Bests"
        leaderboard = users.get_top_text_best(limit)
        for leader in leaderboard:
            leaders.append(f"{leader['text_best_average']:,.2f} WPM")
        embed.set_footer(text="Minimum 1,000 Texts Typed")

    elif category == "textstyped":
        title = "Texts Typed"
        leaderboard = users.get_most("texts_typed", limit)
        for leader in leaderboard:
            leaders.append(f"{leader['texts_typed']:,}")

    elif category == "textrepeats":
        if text_id is not None:
            text = texts.get_text(text_id)
            if not text:
                return await ctx.send(embed=errors.unknown_text())
            title = f"Text #{text_id} Repeats"
            leaderboard = texts.get_text_repeat_leaderboard(text_id)
            for leader in leaderboard:
                print(dict(leader))
                leaders.append(
                    f"[{leader['times']:,} times]"
                    f"({urls.trdata_text_races(leader['username'], text_id)})"
                )
            embed.url = urls.trdata_text(text_id)
        else:
            title = "Text Repeats"
            leaderboard = users.get_most("max_quote_times", limit)
            for leader in leaderboard:
                leaders.append(
                    f"{leader['max_quote_times']:,} times - [Text #{leader['max_quote_id']}]"
                    f"({urls.trdata_text_races(leader['username'], leader['max_quote_id'])})"
                )

    elif category == "totaltextwpm":
        title = "Total Text WPM"
        leaderboard = users.get_most("text_wpm_total", limit)
        for leader in leaderboard:
            leaders.append(f"{leader['text_wpm_total']:,.0f} WPM ({leader['texts_typed']:,} texts)")

    elif category == "wpm":
        title = "Best WPM"
        leaderboard = users.get_most("wpm_best", limit)
        for leader in leaderboard:
            leaders.append(f"{leader['wpm_best']:,.2f} WPM")

    elif category == "racetime":
        title = "Race Time"
        leaderboard = users.get_most("seconds", limit)
        for leader in leaderboard:
            leaders.append(f"{utils.format_duration_short(leader['seconds'])}")

    elif category == "characters":
        title = "Characters Typed"
        leaderboard = users.get_most("characters", limit)
        for leader in leaderboard:
            leaders.append(f"{leader['characters']:,}")

    else:
        top = 10
        if category.isnumeric():
            top = int(category)
        title = f"Top {top} Appearances"
        leaderboard, text_count = top_tens.get_top_n_counts(top)
        for leader in leaderboard:
            leaders.append(f"{leader[1]:,}")

        for i, leader in enumerate(leaderboard):
            rank = utils.rank(i + 1)
            username = utils.escape_discord_format(leader[0])
            leaderboard_string += f"{rank} {username} - {leaders[i]}\n"

        embed.set_footer(text=f"{text_count:,} total texts")

    if category != "toptens" and not category.isnumeric():
        for i, leader in enumerate(leaderboard):
            rank = utils.rank(i + 1)
            username = utils.escape_discord_format(leader["username"])
            flag = f":flag_{leader['country']}: " if leader['country'] else ""
            leaderboard_string += f"{rank} {flag}{username} - {leaders[i]}\n"

    embed.title = f"{title} Leaderboard"
    embed.description = leaderboard_string

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
