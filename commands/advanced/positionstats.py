from discord import Embed
from discord.ext import commands
import errors
import urls
import utils
from database.bot_users import get_user
from commands.basic.stats import get_params
import database.users as users
import database.races as races

info = {
    "name": "positionstats",
    "aliases": ["ps"],
    "description": "Displays stats about the positions of a user's races",
    "parameters": "[username]",
    "usages": ["positionstats keegant"],
    "import": True,
}

class PositionStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def positionstats(self, ctx, *params):
        user = get_user(ctx)

        try:
            username = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username)

async def run(ctx, user, username):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    columns = ["number", "rank", "racers"]
    race_list = races.get_races(username, columns=columns, order_by="number")

    result_dict = {}
    race_count = len(race_list)
    wins = 0
    most_racers = (0, 0, 0)
    biggest_win = (0, 0, 0)
    biggest_loss = (0, 0, 1)
    win_streak = (0, 0, 0)
    current_win_streak = 0

    for race in race_list:
        number, rank, racers = race
        result = f"{rank}/{racers}"
        if result in result_dict:
            result_dict[result] += 1
        else:
            result_dict[result] = 1

        if racers > most_racers[2]:
            most_racers = (number, rank, racers)

        if rank == 1:
            if racers > biggest_win[2]:
                biggest_win = (number, rank, racers)
            if racers > 1:
                wins += 1
            current_win_streak += 1
        else:
            if current_win_streak > win_streak[0]:
                win_streak = (current_win_streak, number - current_win_streak, number - 1)
            current_win_streak = 0

        if rank > biggest_loss[2]:
            biggest_loss = (number, rank, racers)

    if wins > 0 and win_streak[0] == 0:
        win_streak = (race_count, 1, race_count)

    win_percent = (wins / race_count) * 100
    sorted_results = sorted(result_dict.items(), key=lambda x: x[1], reverse=True)
    description = (
        f"**Races:** {race_count:,}\n"
        f"**Wins:** {wins:,} ({win_percent:,.2f}%)\n"
        f"**Most Racers:** {most_racers[1]}/{most_racers[2]:,} "
        f"(Race [#{most_racers[0]:,}]({urls.replay(username, most_racers[0])}))\n"
    )

    if wins > 0:
        description += (
            f"**Biggest Win:** {biggest_win[1]}/{biggest_win[2]:,} "
            f"(Race [#{biggest_win[0]:,}]({urls.replay(username, biggest_win[0])}))\n"
        )

    if biggest_loss[0] != 0:
        description += (
            f"**Biggest Loss:** {biggest_loss[1]}/{biggest_loss[2]:,} "
            f"(Race [#{biggest_loss[0]:,}]({urls.replay(username, biggest_loss[0])}))\n"
        )

    if wins > 0:
        description += (
            f"**Longest Win Streak:** {win_streak[0]:,} "
            f"(Races [#{win_streak[1]:,}]({urls.replay(username, win_streak[1])}) - "
            f"[#{win_streak[2]:,}]({urls.replay(username, win_streak[2])}))\n"
        )

    description += "\n**Positions**\n"

    for result, frequency in sorted_results[:20]:
        description += f"**{result}:** {frequency:,}\n"

    embed = Embed(
        title="Position Stats",
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PositionStats(bot))