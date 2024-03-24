from discord import Embed
from discord.ext import commands
from src import errors, utils
import database.competition_results as competition_results
from database.bot_users import get_user
from api.users import get_stats
from commands.basic.stats import get_params

info = {
    "name": "awards",
    "aliases": ["medals", "aw", "md"],
    "description": "Displays a breakdown of a user's competition awards",
    "parameters": "[username]",
    "usages": ["awards keegant"],
    "import": False,
}


class Awards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    # @commands.before_invoke(lock_command)
    async def awards(self, ctx, *params):
        user = get_user(ctx)

        try:
            username = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username)


async def run(ctx, user, username):
    stats = get_stats(username)
    if not stats:
        return await ctx.send(embed=errors.invalid_username())

    awards = competition_results.get_awards(username)
    total = awards["total"]

    embed = Embed(title=f"Awards ({total:,})", color=user["colors"]["embed"])
    utils.add_profile(embed, stats)

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

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Awards(bot))
