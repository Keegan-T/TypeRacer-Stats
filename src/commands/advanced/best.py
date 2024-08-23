from discord import Embed
from discord.ext import commands

import commands.recent as recent
import database.races as races
import database.texts as texts
import database.users as users
from database.bot_users import get_user
from utils import errors, urls, strings, embeds

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

        result = get_args(user, args, command)
        if embeds.is_embed(result):
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
    if embeds.is_embed(result):
        return result

    username, category = result

    if "text_id" in params:
        text_id = category
        category = None

    return username, category, text_id


async def run(ctx, user, username, category, text_id, reverse=True):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    text_list = texts.get_texts(as_dictionary=True, universe=universe)
    limit = 10

    if text_id is not None:
        text_id = int(text_id)
        if text_id not in text_list:
            return await ctx.send(embed=errors.unknown_text(universe))
        text = text_list[text_id]
        text["text_id"] = text_id
        race_list = races.get_text_races(username, text_id, universe)
        race_list.sort(key=lambda x: x["wpm"], reverse=reverse)
        race_list = race_list[:limit]
        limit = len(race_list)
        embed = Embed()
        embed.color = user["colors"]["embed"]
        embeds.add_profile(embed, stats, universe)
        embeds.add_universe(embed, universe)
        recent.text_id = text_id

        if limit == 0:
            description = strings.text_description(text, universe)
            embed.title = f"Top 10 {'Best' if reverse else 'Worst'} Races"
            embed.description = (
                f"{description}\n\n"
                f"User has no races on this text\n"
                f"[Race this text]({text['ghost']})"
            )
            return await ctx.send(embed=embed)

        top = ""
        average = 0

        for race in race_list:
            score = f"{race['wpm']:,.2f} WPM"
            average += race["wpm"]
            top += (
                f"[{score}]"
                f"({urls.replay(username, race['number'], universe)})"
                f" - Race #{race['number']:,} - "
                f"<t:{int(race['timestamp'])}:R>\n"
            )

        average /= limit
        average_score = f"{average:,.2f} WPM"

        top = (
            f"{strings.text_description(text, universe)}\n\n"
            f"**{'Best' if reverse else 'Worst'} {limit} Average:** {average_score}\n\n"
            f"{top}"
        )

        embed.title = f"Top {limit} {'Best' if reverse else 'Worst'} Races"
        embed.description = top

    else:
        race_list = await races.get_races(
            username, with_texts=True, order_by=category,
            reverse=reverse, limit=limit, universe=universe
        )
        limit = len(race_list)
        top = ""
        average = 0

        for race in race_list:
            quote = strings.truncate_clean(race["quote"], 60)
            text_id = race["text_id"]
            if category == "wpm":
                score = f"{race['wpm']:,.2f} WPM"
            else:
                score = f"{race['points']:,.2f} points"
            average += race[category]
            top += (
                f"[{score}]"
                f"({urls.replay(username, race['number'], universe)})"
                f" - Race #{race['number']:,} - "
                f"[Text #{text_id}]({urls.trdata_text(text_id, universe)}) - "
                f"<t:{int(race['timestamp'])}:R>\n\"{quote}\"\n\n"
            )

        average /= limit
        average_score = f"{average:,.2f} " + "WPM" if category == "wpm" else "points"

        top = f"**{'Best' if reverse else 'Worst'} {limit} Average:** {average_score}\n\n" + top

        embed = Embed(
            title=f"Top {limit} {'Best' if reverse else 'Worst'} Races ({'WPM' if category == 'wpm' else 'Points'})",
            description=top,
            color=user["colors"]["embed"],
        )

    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Best(bot))
