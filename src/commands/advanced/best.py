from discord.ext import commands

import commands.recent as recent
import database.races as races
import database.texts as texts
import database.users as users
from database.bot_users import get_user
from utils import errors, urls, strings, dates
from utils.embeds import Message, Page, get_pages, is_embed

categories = ["wpm", "points"]
command = {
    "name": "best",
    "aliases": ["top"],
    "description": "Displays a user's top 10 best races in a category\n"
                   "Provide a text ID to see best races for a specific text",
    "parameters": "[username] <category/text_id>",
    "defaults": {
        "category": "wpm",
    },
    "usages": [
        "best hospitalforsouls2 wpm",
        "best joshua728 points",
        "best keegant 3810446",
    ],
}


class Best(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def best(self, ctx, *args):
        user = get_user(ctx)
        args, user = dates.set_command_date_range(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, category, text_id = result
        await run(ctx, user, username, category, text_id)


def get_args(user, args, info):
    text_id = None

    if len(args) == 2 and args[1].isnumeric():
        params = "username text_id"
    else:
        params = f"username category:{'|'.join(categories)}"

    result = strings.parse_command(user, params, args, info)
    if is_embed(result):
        return result

    username, category = result

    if "text_id" in params:
        text_id = category
        category = "wpm"

    return username, category, text_id


async def run(ctx, user, username, category, text_id, reverse=True):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    category_title = "WPM" if category == "wpm" else "Points"
    sort_title = "Best" if reverse else "Worst"
    title = f"{sort_title} Races"
    header = ""
    text_list = texts.get_texts(as_dictionary=True, universe=universe)

    if text_id is not None:
        text_id = int(text_id)
        if text_id not in text_list:
            return await ctx.send(embed=errors.unknown_text(universe))

        text = text_list[text_id]
        text["text_id"] = text_id
        race_list = races.get_text_races(username, text_id, universe, user["start_date"], user["end_date"])
        race_list.sort(key=lambda x: x["wpm"], reverse=reverse)
        race_list = race_list[:100]
        recent.text_id = text_id

        if not race_list:
            description = (
                f"{strings.text_description(text, universe)}\n\n"
                f"User has no races on this text\n"
                f"[Race this text]({text['ghost']})"
            )
            message = Message(
                ctx=ctx,
                user=user,
                pages=Page(description=description),
                title=title,
                profile=stats,
                universe=universe,
            )

            return await message.send()

        def formatter(race):
            return (
                f"[{race['wpm']:,.2f} WPM]"
                f"({urls.replay(username, race['number'], universe)})"
                f" - Race #{race['number']:,} - "
                f"{strings.discord_timestamp(race['timestamp'])}\n"
            )

        header = strings.text_description(text, universe) + "\n\n"

    else:
        race_list = await races.get_races(
            username, with_texts=True, order_by=category,
            reverse=reverse, limit=100, universe=universe,
            start_date=user["start_date"], end_date=user["end_date"]
        )
        if not race_list:
            return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

        def formatter(race):
            quote = strings.truncate_clean(race["quote"], 60)
            text_id = race["text_id"]
            return (
                f"[{race[category]:,.2f} {category_title}]"
                f"({urls.replay(username, race['number'], universe)})"
                f" - Race #{race['number']:,} - "
                f"[Text #{text_id}]({urls.trdata_text(text_id, universe)}) - "
                f"{strings.discord_timestamp(race['timestamp'])}\n\"{quote}\"\n\n"
            )

        title += f" ({category_title})"

    pages = get_pages(race_list, formatter, page_count=10, per_page=10)
    limit = min(10, len(race_list))
    top_10_average = sum([race[category] for race in race_list[:10]]) / limit
    header += (
        f"**{sort_title} {limit} Average:** "
        f"{top_10_average:,.2f} {category_title}\n\n"
    )

    message = Message(
        ctx=ctx,
        user=user,
        pages=pages,
        title=title,
        header=header,
        profile=stats,
        universe=universe,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Best(bot))
