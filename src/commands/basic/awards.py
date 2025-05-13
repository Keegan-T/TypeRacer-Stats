from discord import Embed, File
from discord.ext import commands

import database.competition_results as competition_results
from api.users import get_stats
from commands.basic.stats import get_args
from config import prefix
from database.bot_users import get_user
from graphs import awards_graph
from graphs.core import remove_file
from utils import errors, embeds, strings

graph_commands = ["awardsgraph", "medalsgraph", "awg"]
command = {
    "name": "awards",
    "aliases": ["medals", "aw"] + graph_commands,
    "description": "Displays a breakdown of a user's competition awards\n"
                   f"Use `{prefix}awardsgraph` to display a graph of awards",
    "parameters": "[username]",
    "usages": ["awards keegant", "awardsgraph keegant"],
    "multiverse": False,
}


class Awards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def awards(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username, ctx.invoked_with in graph_commands)


async def run(ctx, user, username, show_graph):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())
    era_string = strings.get_era_string(user)

    awards = await competition_results.get_awards(username, user["start_date"], user["end_date"])
    total = awards["total"]

    embed = Embed(
        title=f"Awards ({total:,})",
        url=f"https://data.typeracer.com/pit/award_history?user={username}",
        color=user["colors"]["embed"]
    )
    embeds.add_profile(embed, stats)

    if total == 0:
        embed.description = "No awards"
        return await ctx.send(embed=embed)

    kinds = ["year", "month", "week", "day"]
    ranks = ["first", "second", "third"]

    counts = [0, 0, 0]
    field_strings = ["", "", ""]

    for kind in kinds:
        kind_title = "Daily" if kind == "day" else kind.title() + "ly"
        for i, rank in enumerate(ranks):
            count = awards[kind][rank]
            counts[i] += count
            if count > 0:
                field_strings[i] += f"**{kind_title}:** {count:,}\n"

    for i, count in enumerate(counts):
        if count > 0:
            embed.add_field(name=f":{ranks[i]}_place: x{count}", value=field_strings[i])

    if not show_graph:
        return await ctx.send(embed=embed, content=era_string)

    file_name = f"awards_{username}.png"
    await awards_graph.render(user, username, file_name)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file, content=era_string)

    remove_file(file_name)


async def setup(bot):
    await bot.add_cog(Awards(bot))
