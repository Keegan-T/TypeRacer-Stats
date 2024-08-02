from discord import Embed, File
from discord.ext import commands

import database.races as races
import database.users as users
from database.bot_users import get_user
from graphs import personal_best_graph
from graphs.core import remove_file
from utils import errors, urls, embeds, strings

categories = ["races", "time"]
command = {
    "name": "personalbestgraph",
    "aliases": ["pbg"],
    "description": "Displays a graph of a user's personal best WPM over races/time",
    "parameters": "[username] <category>",
    "defaults": {
        "category": "races"
    },
    "usages": ["personalbestgraph keegant time", "personalbestgraph poem races"],
}


class PersonalBestGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def personalbestgraph(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, category = result
        await run(ctx, user, username, category)


def get_args(user, args, info):
    params = f"username category:{'|'.join(categories)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, category):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    column = 2 if category == "time" else 1
    race_list = await races.get_races(username, columns=["wpm", "number", "timestamp"], universe=universe)
    race_list.sort(key=lambda r: r[1])

    pbs = [race_list[0]]
    y = [race_list[0][0]]
    x = [race_list[0][column]]

    for race in race_list:
        wpm = race[0]
        if y[-1] < wpm:
            pbs.append(race)
            y.append(wpm)
            x.append(race[column])

    indicator = f"#{pbs[0]['number']:,}" if category == "races" else f"<t:{int(pbs[0]['timestamp'])}:R>"
    description = (
        f"**First Race:** [{pbs[0]['wpm']:,.2f} WPM]"
        f"({urls.replay(username, pbs[0]['number'], universe)}) - {indicator}\n"
    )

    latest_break = None

    for i in range(len(pbs) - 1):
        current_pb = pbs[i]["wpm"]
        next_pb = pbs[i + 1]
        next_wpm = next_pb["wpm"]
        next_number = next_pb["number"]
        next_indicator = f"#{next_number:,}" if category == "races" else f"<t:{int(next_pb['timestamp'])}:R>"
        next_barrier = next_wpm - (next_wpm % 10)

        if next_barrier > current_pb:
            latest_break = next_pb
            label = f"**Best Race:**" if i == len(pbs) - 2 else f"**Broke {next_barrier:.0f}:**"
            description += (
                f"{label} [{next_wpm:,.2f} WPM]"
                f"({urls.replay(username, next_pb['number'], universe)}) - "
                f"{next_indicator}\n"
            )

    if latest_break != pbs[-1]:
        indicator = f"#{pbs[-1]['number']:,}" if category == "races" else f"<t:{int(pbs[-1]['timestamp'])}:R>"
        description += (
            f"**Best Race:** [{pbs[-1]['wpm']:,.2f} WPM]"
            f"({urls.replay(username, pbs[-1]['number'], universe)}) - "
            f"{indicator}\n"
        )

    embed = Embed(
        title=f"Personal Best Progression",
        description=description,
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, stats, universe)
    embeds.add_universe(embed, universe)

    file_name = f"personal_best_over_{category}_{username}.png"
    personal_best_graph.render(user, username, x, y, category, file_name, universe)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    remove_file(file_name)


async def setup(bot):
    await bot.add_cog(PersonalBestGraph(bot))
