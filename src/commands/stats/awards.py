from discord.ext import commands

import database.main.competition_results as competition_results
from api.users import get_stats
from commands.stats.stats import get_args
from config import prefix
from database.bot.users import get_user
from graphs import awards_graph
from utils import errors
from utils.embeds import Page, Message, is_embed, Field

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
        if is_embed(result):
            return await ctx.send(embed=result)

        username = result
        await run(ctx, user, username, ctx.invoked_with in graph_commands)


async def run(ctx, user, username, show_graph):
    stats = await get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    awards = await competition_results.get_awards(username, user["start_date"], user["end_date"])
    total = awards["total"]
    periods = ["year", "month", "week", "day"]
    ranks = ["first", "second", "third"]
    fields = []

    for i, rank in enumerate(ranks):
        field_string = ""
        rank_count = 0
        for period in periods:
            count = awards[period][rank]
            rank_count += count
            if count > 0:
                period_title = "Daily" if period == "day" else period.title() + "ly"
                field_string += f"**{period_title}:** {count:,}\n"
        if field_string:
            fields.append(Field(
                name=f":{ranks[i]}_place: x{rank_count:,}",
                value=field_string,
            ))

    render = None
    description = "No awards"
    if total > 0:
        description = ""
        if show_graph:
            competitions = list(await competition_results.get_competitions(user["start_date"], user["end_date"]))
            competitions.sort(key=lambda x: x["end_time"])
            render = lambda: awards_graph.render(user, username, competitions)

    page = Page(
        title=f"Awards ({total:,})",
        description=description,
        fields=fields,
        render=render,
    )

    message = Message(
        ctx, user, page,
        url=f"https://data.typeracer.com/pit/award_history?user={username}",
        profile=stats,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Awards(bot))
