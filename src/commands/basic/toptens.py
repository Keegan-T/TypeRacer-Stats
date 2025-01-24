import json

from discord import Embed, File
from discord.ext import commands

import database.text_results as top_tens
import database.users as users
from api.users import get_stats
from commands.basic.stats import get_args
from config import prefix
from database.bot_users import get_user
from graphs.core import remove_file
from utils import errors, urls, strings, embeds, dates

command = {
    "name": "toptens",
    "aliases": ["top10s", "10s"],
    "description": "Displays the number of text top 10s a user appears in\n"
                   f"`{prefix}top10s [username] best` will display a user's best top 10 performances\n"
                   f"`{prefix}top10s [username] export` will attach a file listing all of a user's top 10s",
    "parameters": "[username]",
    "usages": [
        "toptens joshua728"
        "toptens keegant best"
        "toptens flaneur export"
    ],
    "multiverse": False,
    "temporal": False,
}


class TopTens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def toptens(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        best = False
        if len(args) > 1:
            if args[1] == "best":
                best = True
            elif args[1] == "export":
                return await export(ctx, username)

        await run(ctx, user, username, best)


async def export(ctx, username):
    top_10s = top_tens.get_top_10s()
    export_data = {
        "timestamp": dates.now().timestamp(),
        "1": [], "2": [], "3": [], "4": [], "5": [],
        "6": [], "7": [], "8": [], "9": [], "10": [],
        "missing": [],
    }

    for text_id, top_10 in top_10s.items():
        usernames = [score["username"] for score in top_10]
        try:
            index = usernames.index(username)
            export_data[str(index + 1)].append(text_id)
        except ValueError:
            export_data["missing"].append(text_id)

    file_name = f"{username}_top_10s.json"
    json_data = json.dumps(export_data)
    with open(file_name, "w") as file:
        file.write(json_data)

    await ctx.send(file=File(file_name))

    remove_file(file_name)


async def run(ctx, user, username, best):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    embed = Embed(title="Top 10 Rankings", color=user["colors"]["embed"])
    embeds.add_profile(embed, stats)

    top_10_counts = top_tens.get_top_10_counts(username)
    top_10_count = sum(top_10_counts)
    total_texts = top_tens.get_count()

    if top_10_count == 0:
        embed.description = "User does not rank in any top 10s"
        return await ctx.send(embed=embed)

    texts_typed = users.get_texts_typed(username)
    total_appearance_percent = (top_10_count / total_texts) * 100
    typed_appearance_percent = (top_10_count / texts_typed) * 100

    embed.description = (
        f"**Appearances:** {top_10_count:,}\n"
        f"**Texts Typed:**  {texts_typed:,} ({typed_appearance_percent:,.2f}%)\n"
        f"**Total Texts:** {total_texts:,} ({total_appearance_percent:,.2f}%)"
    )

    if best:
        top_10s = top_tens.get_top_10s()
        performances = []

        for text_id in top_10s:
            top_10 = top_10s[text_id]
            for i in range(len(top_10)):
                race = dict(top_10[i])
                race["lead"] = 0
                race["text_id"] = text_id
                if race["username"] == username:
                    race["position"] = i + 1
                    if i == 0:
                        if len(top_10) > 1:
                            next_race = top_10[i + 1]
                            race["lead"] = race["wpm"] - next_race["wpm"]
                    performances.append(race)

        races_string = ""
        performances.sort(key=lambda x: (x["position"], -x["lead"], -x["wpm"]))
        for race in performances[:20]:
            race_string = (
                f"[{race['wpm']:,.2f} WPM]({urls.replay(username, race['number'])}) - "
                f"[Position #{race['position']}]({urls.trdata_text(race['text_id'])}&highlight={username})"
            )
            if race["lead"] > 0:
                race_string += f" by {race['lead']:,.2f} WPM"
            races_string += race_string + "\n"

        embed.description += "\n\n**Best Performances**\n" + races_string

    else:
        top_10_counts_string = ""
        top_10_cumulative_string = ""

        for i, number in enumerate(top_10_counts):
            number = i + 1
            count = top_10_counts[i]
            if count == 0:
                continue
            top_10_counts_string += f"**{strings.get_display_number(number)}:** {count:,}\n"
            top_10_cumulative_string += f"**Top {number}:**. {sum(top_10_counts[:i + 1]):,} \n"

        embed.add_field(name="Position Counts", value=top_10_counts_string)
        embed.add_field(name="Cumulative Counts", value=top_10_cumulative_string)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TopTens(bot))
