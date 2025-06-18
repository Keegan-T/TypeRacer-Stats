import json

from discord import File
from discord.ext import commands

import database.main.competition_results as competition_results
import database.main.text_results as top_tens
import database.main.texts as texts
import database.main.users as users
from commands.locks import leaderboard_lock
from config import prefix
from database.bot.users import get_user
from database.main.alts import get_alts
from utils import errors, urls, strings, dates, files
from utils.embeds import Page, Message
from utils.errors import command_in_use

categories = [
    "races", "wins", "points", "awards", "textbests", "textstyped", "toptens", "textrepeats",
    "totaltextwpm", "wpm", "racetime", "characters", "captcha", "racesover", "textsover", "performance"
]
command = {
    "name": "leaderboard",
    "aliases": ["lb"],
    "description": "Displays the top 10 users in a category\n"
                   f"`{prefix}leaderboard [n]` will show top n appearances",
    "parameters": "[category]",
    "usages": [f"leaderboard {category}" for category in categories],
    "multiverse": False,
    "temporal": False,
}


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def leaderboard(self, ctx, *args):
        if leaderboard_lock.locked():
            return await ctx.send(embed=command_in_use())

        async with leaderboard_lock:
            user = get_user(ctx)
            secondary = None

            if not args:
                return await ctx.send(embed=errors.missing_argument(command))

            category_string = args[0]

            if category_string.isnumeric() and 1 <= int(category_string) <= 10:
                category = category_string
            else:
                category = strings.get_category(categories, category_string)
                if not category:
                    return await ctx.send(embed=errors.invalid_choice("category", categories))

            if len(args) > 1:
                secondary = args[1]

            await run(ctx, user, category, secondary)


async def run(ctx, user, category, secondary):
    page = Page()
    url = None

    if category == "races":
        title = "Races"
        description = leaderboard_races()

    elif category == "wins":
        title = "Wins"
        description = leaderboard_wins()

    elif category == "points":
        title = "Points"
        description = leaderboard_points()

    elif category == "awards":
        title = "Awards"
        description = leaderboard_awards()
        total_competitions = competition_results.get_competition_count()
        page.footer = f"Across {total_competitions:,} competitions"

    elif category == "textbests":
        title = "Text Bests"
        description = leaderboard_text_bests()
        text_count = texts.get_text_count()
        min_texts = int(text_count * 0.2)
        page.footer = f"Minimum {min_texts:,} Texts Typed (20%)"

    elif category == "textstyped":
        title = "Texts Typed"
        description = leaderboard_texts_typed()

    elif category == "textrepeats":
        if secondary is None:
            title = "Text Repeats"
            description = leaderboard_text_repeats()
        else:
            text_id = secondary
            text = texts.get_text(text_id)
            if not text:
                return await ctx.send(embed=errors.unknown_text())
            title = f"Text #{text_id} Repeats"
            description = leaderboard_text_id_repeats(text_id)
            url = urls.trdata_text(text_id)

    elif category == "totaltextwpm":
        title = "Total Text WPM"
        description = leaderboard_total_text_wpm()

    elif category == "wpm":
        title = "Best WPM"
        description = leaderboard_wpm()

    elif category == "racetime":
        title = "Race Time"
        description = leaderboard_race_time()

    elif category == "characters":
        title = "Characters Typed"
        description = leaderboard_characters()

    elif category == "captcha":
        title = "Captcha WPM"
        description = leaderboard_captcha()

    elif category in ["racesover", "textsover"]:
        try:
            wpm = float(secondary)
        except (ValueError, TypeError):
            return await ctx.send(embed=errors.invalid_number_format())

        if category == "racesover":
            title = f"Races Over {wpm:,.0f} WPM"
            description = await leaderboard_races_over(wpm)

        elif category == "textsover":
            title = f"Texts Over {wpm:,.0f} WPM"
            description = await leaderboard_texts_over(wpm)

    elif category == "performance":
        title = "Performance"
        description = await leaderboard_performance()

    else:
        n = 10
        if category.isnumeric():
            n = int(category)

        if secondary == "export":
            return await export_top_n(ctx, n)

        title = f"Top {n} Appearances"
        description, text_count, user_count = leaderboard_top_n(n)
        page.footer = f"{text_count:,} total texts\n{user_count:,} total users"

    page.title = title + " Leaderboard"
    page.description = description

    message = Message(
        ctx, user, page,
        url=url,
    )

    await message.send()


def filter_users(user_list):
    countries = users.get_countries()
    alts = get_alts()
    filtered = []
    added_users = set()

    i = 0
    for user in user_list:
        user = dict(user)
        username = user["username"]
        alt_accounts = {username} | set(alts.get(username, []))

        if not alt_accounts & added_users:
            user["country"] = countries.get(username, None)
            filtered.append(user)
            added_users.update(alt_accounts)
            i += 1
            if i == 20:
                break

    return filtered


def user_rank(user, i):
    flag = f":flag_{user['country']}: " if user['country'] else ""
    return f"{strings.rank(i + 1)} {flag}{user['username']}"


def leaderboard_races():
    leaders = filter_users(users.get_most("races", 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['races']:,}\n"

    return description


def leaderboard_wins():
    leaders = filter_users(users.get_most("wins", 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['wins']:,}\n"

    return description


def leaderboard_points():
    leaders = filter_users(users.get_most_total_points(30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['points_total']:,.0f}\n"

    return description


def leaderboard_awards():
    leaders = filter_users(users.get_most_awards(30))
    description = ""
    for i, leader in enumerate(leaders):
        first = leader["awards_first"]
        second = leader["awards_second"]
        third = leader["awards_third"]
        total = first + second + third
        description += (
            f"{user_rank(leader, i)} - {total:,} - :first_place: x{first:,} "
            f":second_place: x{second:,} :third_place: x{third:,}\n"
        )

    return description


def leaderboard_text_bests():
    leaders = filter_users(users.get_top_text_best(30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['text_best_average']:,.2f} WPM\n"

    return description


def leaderboard_texts_typed():
    leaders = filter_users(users.get_most_texts_typed(30))
    description = ""
    for i, leader in enumerate(leaders):
        min_repeats = leader["min_repeats"]
        repeat_string = ""
        if min_repeats > 1:
            repeat_string = f" ({min_repeats}x each)"
        description += f"{user_rank(leader, i)} - {leader['texts_typed']:,}{repeat_string}\n"

    return description


def leaderboard_text_repeats():
    leaders = filter_users(users.get_most("text_repeat_times", 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += (
            f"{user_rank(leader, i)} - "
            f"{leader['text_repeat_times']:,} times - [Text #{leader['text_repeat_id']}]"
            f"({urls.trdata_text_races(leader['username'], leader['text_repeat_times'])})\n"
        )

    return description


def leaderboard_text_id_repeats(text_id):
    leaders = filter_users(texts.get_text_repeat_leaderboard(text_id, 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += (
            f"{user_rank(leader, i)} - "
            f"[{leader['times']:,} times]"
            f"({urls.trdata_text_races(leader['username'], text_id)})\n"
        )

    return description


def leaderboard_total_text_wpm():
    leaders = filter_users(users.get_most("text_wpm_total", 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += (
            f"{user_rank(leader, i)} - "
            f"{leader['text_wpm_total']:,.0f} WPM ({leader['texts_typed']:,} texts)\n"
        )

    return description


def leaderboard_wpm():
    leaders = filter_users(users.get_most("wpm_best", 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['wpm_best']:,.2f} WPM\n"

    return description


def leaderboard_race_time():
    leaders = filter_users(users.get_most("seconds", 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {strings.format_duration_short(leader['seconds'])}\n"

    return description


def leaderboard_characters():
    leaders = filter_users(users.get_most("characters", 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['characters']:,}\n"

    return description


def leaderboard_captcha():
    leaders = filter_users(users.get_most("wpm_verified", 50))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['wpm_verified']:,.2f} WPM\n"

    return description


async def leaderboard_races_over(wpm):
    leaders = filter_users(await users.get_most_races_over(wpm, 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['races_over']:,}\n"

    return description


async def leaderboard_texts_over(wpm):
    leaders = filter_users(await users.get_most_texts_over(wpm, 30))
    description = ""
    for i, leader in enumerate(leaders):
        description += f"{user_rank(leader, i)} - {leader['texts_over']:,}\n"

    return description


async def leaderboard_performance():
    leaders = filter_users(await users.get_most_performance())
    description = ""
    for i, leader in enumerate(leaders):
        description += (
            f"{user_rank(leader, i)} - {leader['performance']:,.0f} "
            f"({leader['text_best_average']:,.2f} TB, {leader['texts_typed']:,} texts)\n"
        )

    return description


def leaderboard_top_n(n):
    countries = users.get_countries()
    leaders, text_count = top_tens.get_top_n_counts(n)
    description = ""
    for i, leader in enumerate(leaders[:20]):
        leader = {
            "username": leader[0],
            "count": leader[1],
            "country": countries.get(leader[0], None),
        }
        description += f"{user_rank(leader, i)} - {leader["count"]:,}\n"

    return description, text_count, len(leaders)


async def export_top_n(ctx, n):
    leaders, text_count = top_tens.get_top_n_counts(n)
    export_data = {
        "timestamp": dates.now().timestamp(),
        "total_texts": text_count,
        "users": []
    }

    for i, leader in enumerate(leaders):
        username, appearances = leader
        export_data["users"].append({
            "username": username,
            "appearances": appearances,
        })

    file_name = f"top_{n}_appearances.json"
    json_data = json.dumps(export_data)
    with open(file_name, "w") as file:
        file.write(json_data)

    await ctx.send(file=File(file_name))

    files.remove_file(file_name)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
