from discord import Embed
from discord.ext import commands
import errors
import urls
import utils
from database.bot_users import get_user
import commands.recent as recent
import database.users as users
import database.races as races
import database.texts as texts

categories = ["wpm", "points"]
info = {
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
    "import": True,
}


class Best(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def best(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, category, text_id = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, category, text_id)


async def get_params(ctx, user, params, command=info):
    username = user["username"]
    category = "wpm"
    text_id = None

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        if params[1] == "^":
            text_id = int(recent.text_id)
        elif params[1].isnumeric():
            text_id = int(params[1])
        else:
            category = utils.get_category(categories, params[1])
            if not category:
                await ctx.send(embed=errors.invalid_option("category", categories))
                raise ValueError


    if not username:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    return username.lower(), category, text_id


async def run(ctx, user, username, category, text_id, reverse=True):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    text_list = texts.get_texts(as_dictionary=True)
    limit = 10
    if text_id is not None:
        if text_id not in text_list:
            return await ctx.send(embed=errors.unknown_text())
        text = text_list[text_id]
        race_list = sorted(races.get_text_races(username, text_id), key=lambda x: x["wpm"], reverse=reverse)[:limit]

        limit = len(race_list)

        top = ""
        average = 0

        for race in race_list:
            score = f"{race['wpm']:,.2f} WPM"
            average += race[category]
            top += (
                f"[{score}]"
                f"({urls.replay(username, race['number'])})"
                f" - Race #{race['number']:,} - "
                f"<t:{int(race['timestamp'])}:R>\n"
            )

        average /= limit
        average_score = f"{average:,.2f} WPM"

        top = f"**{'Best' if reverse else 'Worst'} {limit} Average:** {average_score}\n\n" + top
        top = f'"{utils.truncate_clean(text["quote"], 1000)}"\n\n' + top

        embed = Embed(
            title=f"Top {limit} {'Best' if reverse else 'Worst'} Races (Text #{text_id})",
            description=top,
            color=user["colors"]["embed"],
        )

    else:
        race_list = races.get_races(username, with_texts=True, order_by=category, reverse=reverse, limit=limit)

        limit = len(race_list)

        top = ""
        average = 0

        for race in race_list:
            quote = utils.truncate_clean(race["quote"], 60)
            if category == "wpm":
                score = f"{race['wpm']:,.2f} WPM"
            else:
                score = f"{race['points']:,.2f} points"
            average += race[category]
            top += (
                f"[{score}]"
                f"({urls.replay(username, race['number'])})"
                f" - Race #{race['number']:,} - Text #{race['text_id']} - "
                f"<t:{int(race['timestamp'])}:R>\n{quote}\n\n"
            )

        average /= limit
        average_score = f"{average:,.2f} " + "WPM" if category == "wpm" else "points"

        top = f"**{'Best' if reverse else 'Worst'} {limit} Average:** {average_score}\n\n" + top

        embed = Embed(
            title=f"Top {limit} {'Best' if reverse else 'Worst'} Races ({'WPM' if category == 'wpm' else 'Points'})",
            description=top,
            color=user["colors"]["embed"],
        )

    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)
    if text_id is not None:
        recent.text_id = text_id


async def setup(bot):
    await bot.add_cog(Best(bot))
