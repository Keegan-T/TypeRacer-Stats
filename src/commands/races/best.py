from discord.ext import commands

import database.main.races as races
import database.bot.recent_text_ids as recent
import database.main.texts as texts
import database.main.users as users
from database.bot.users import get_user
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
        args, user = strings.set_wpm_metric(args, user)

        result = get_args(user, args, command, ctx.channel.id)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, category, text_id = result
        await run(ctx, user, username, category, text_id)


def get_args(user, args, info, channel_id):
    text_id = None

    if len(args) == 2 and (args[1].isnumeric() or args[1] == "^"):
        params = "username text_id"
    else:
        params = f"username category:{'|'.join(categories)}"

    result = strings.parse_command(user, params, args, info, channel_id)
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
    text_pool = user["settings"]["text_pool"]
    wpm_metric = user["settings"]["wpm"]

    category_title = {"wpm": "WPM"}.get(category, category.title())
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
        race_list = races.get_text_races(username, text_id, universe, user["start_date"], user["end_date"], wpm=wpm_metric)
        race_list.sort(key=lambda x: x["wpm"], reverse=reverse)
        race_list = race_list[:100]
        recent.update_recent(ctx.channel.id, text_id)

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
                f"({urls.replay(username, race['number'], universe, timestamp=race['timestamp'])})"
                f" - Race #{race['number']:,} - "
                f"{strings.discord_timestamp(race['timestamp'])}\n"
            )

        header = strings.text_description(text, universe) + "\n\n"

    else:
        columns = ["text_id", "number", wpm_metric, "points", "timestamp"]
        race_list = await races.get_races(
            username, columns=columns, order_by=category, reverse=reverse, limit=100,
            universe=universe, start_date=user["start_date"], end_date=user["end_date"],
            text_pool=text_pool,
        )
        text_list = texts.get_texts(as_dictionary=True, universe=universe)
        if not race_list:
            return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)

        def formatter(race):
            text_id = race["text_id"]
            text = text_list[text_id]
            quote = strings.truncate_clean(text["quote"], 60)
            return (
                f"[{race[category]:,.2f} {category_title}]"
                f"({urls.replay(username, race['number'], universe, timestamp=race['timestamp'])})"
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
        text_pool=text_pool,
        wpm_metric=wpm_metric,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Best(bot))
