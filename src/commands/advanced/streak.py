from discord.ext import commands

import database.main.races as races
import database.main.users as users
from database.bot.users import get_user
from utils import errors, strings, urls
from utils.embeds import Page, Message, is_embed, get_pages

categories = ["wins", "losses", "wpm", "accuracy", "text"]
command = {
    "name": "streak",
    "aliases": ["st"],
    "description": "Displays a user's streak for a given category\n"
                   f"You can use `<n` to show streaks below a given n",
    "parameters": f"[username] <{'|'.join(categories)}> <n>",
    "defaults": {
        "category": "wins",
    },
    "usages": [
        "streak keegant wins",
        "streak keegant losses",
        "streak keegant wpm 100",
        "streak keegant accuracy 99"
    ],
}


# most below wpm/acc with <100


class Streak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def streak(self, ctx, *args):
        user = get_user(ctx)

        args = list(args)
        less_than = False
        if len(args) > 2 and strings.get_category(["wpm", "accuracy"], args[2]):
            args[1], args[2] = args[2], args[1]
            if args[2].startswith("<"):
                args[2] = args[2][1:]
                less_than = True

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, category, n = result
        if category in ["wpm", "accuracy"] and n is None:
            return await ctx.send(embed=errors.missing_argument(command))

        await run(ctx, user, username, category, n, less_than)


def get_args(user, args, info):
    params = f"username category:{'|'.join(categories)} number"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, category, n, less_than):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    columns = ["number", "timestamp"]
    if category in ["wins", "losses"]:
        columns += ["rank", "racers"]
    elif category == "text":
        columns += ["text_id"]
    else:
        columns += [category]
    race_list = await races.get_races(
        username, columns,
        start_date=user["start_date"], end_date=user["end_date"],
        universe=universe,
    )
    race_list.sort(key=lambda x: x["timestamp"])

    windows = []
    current_streak = {"start_index": None, "end_index": None, "streak": 0}
    prev_text_id = -1
    race_count = len(race_list)
    if category == "accuracy" and n > 1:
        n /= 100
    for i, race in enumerate(race_list):
        if category == "wins":
            result = race["rank"] == 1 and race["racers"] > 1
        elif category == "losses":
            result = race["rank"] > 1
        elif category in ["wpm", "accuracy"]:
            if less_than:
                result = race[category] < n
            else:
                result = race[category] >= n
        else:
            text_id = race["text_id"]
            result = text_id == prev_text_id
            prev_text_id = text_id

        if result:
            updated_streak = {"end_index": i}
            if current_streak["streak"] == 0:
                if category == "text":
                    updated_streak["streak"] = 2
                    updated_streak["start_index"] = i - 1
                else:
                    updated_streak["streak"] = 1
                    updated_streak["start_index"] = i
            else:
                updated_streak["streak"] = (
                    race_list[current_streak["end_index"] + 1]["number"]
                    - race_list[current_streak["start_index"]]["number"] + 1
                )
            current_streak.update(updated_streak)
        if not result or i == race_count - 1:
            if current_streak["streak"] > 0:
                windows.append(current_streak.copy())
            current_streak.update({"start_index": None, "end_index": None, "streak": 0})

    def formatter(data):
        start_race = race_list[data["start_index"]]
        end_race = race_list[data["end_index"]]
        start_number = start_race["number"]
        end_number = end_race["number"]
        return (
            f"{data['streak']:,} - Races "
            f"[{start_number:,}]({urls.replay(username, start_number, universe)}) - "
            f"[{end_number:,}]({urls.replay(username, end_number, universe)})\n"
        )

    if not windows:
        pages = Page(description="User has no streaks")
    else:
        windows.sort(key=lambda x: -x["streak"])
        pages = get_pages(windows, formatter, 10, 10)

    title = "Best Streaks - "
    if category in ["wins", "losses"]:
        title += category.title()
    elif category == "wpm":
        direction = "Below" if less_than else "Above"
        title += f"Races {direction} {n:.2f} WPM"
    elif category == "accuracy":
        direction = "Below" if less_than else "Above"
        title += f"Races {direction} {n:.0%} Accuracy"
    elif category == "text":
        title += "Same Text"

    message = Message(
        ctx, user, pages,
        title=title,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Streak(bot))
