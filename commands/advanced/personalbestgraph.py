from discord import Embed, File
from discord.ext import commands
import os
import graphs
import utils
import errors
import urls
from database.bot_users import get_user
import database.users as users
import database.races as races

types = ["races", "time"]
info = {
    "name": "personalbestgraph",
    "aliases": ["pbg"],
    "description": "Displays a graph of a user's personal best WPM over races/time",
    "parameters": "[username] <type>",
    "defaults": {
        "type": "races"
    },
    "usages": ["personalbestgraph keegant time", "personalbestgraph poem races"],
    "import": True,
}


class PersonalBestGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def personalbestgraph(self, ctx, *params):
        user = get_user(ctx)

        username = user["username"]
        kind = "races"

        if params and params[0].lower() != "me":
            username = params[0].lower()

        if len(params) > 1:
            kind = utils.get_category(types, params[1])
            if not kind:
                return await ctx.send(embed=errors.invalid_option("type", types))

        if not username:
            return await ctx.send(embed=errors.missing_param(info))

        await run(ctx, user, username, kind)


async def run(ctx, user, username, kind):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    column = 2 if kind == "time" else 1
    race_list = sorted(await races.get_races(username, columns=["wpm", "number", "timestamp"]), key=lambda r: r[1])

    pbs = [race_list[0]]
    y = [race_list[0][0]]
    x = [race_list[0][column]]

    for race in race_list:
        wpm = race[0]
        if y[-1] < wpm:
            pbs.append(race)
            y.append(wpm)
            x.append(race[column])

    indicator = f"#{pbs[0]['number']:,}" if kind == "races" else f"<t:{int(pbs[0]['timestamp'])}:R>"
    description = (
        f"**First Race:** [{pbs[0]['wpm']:,.2f} WPM]"
        f"({urls.replay(username, pbs[0]['number'])}) - {indicator}\n"
    )

    latest_break = None

    for i in range(len(pbs) - 1):
        current_pb = pbs[i]["wpm"]
        next_pb = pbs[i + 1]
        next_wpm = next_pb["wpm"]
        next_number = next_pb["number"]
        next_indicator = f"#{next_number:,}" if kind == "races" else f"<t:{int(next_pb['timestamp'])}:R>"
        next_barrier = next_wpm - (next_wpm % 10)

        if next_barrier > current_pb:
            latest_break = next_pb
            label = f"**Best Race:**" if i == len(pbs) - 2 else f"**Broke {next_barrier:.0f}:**"
            description += (
                f"{label} [{next_wpm:,.2f} WPM]"
                f"({urls.replay(username, next_pb['number'])}) - "
                f"{next_indicator}\n"
            )

    if latest_break != pbs[-1]:
        indicator = f"#{pbs[-1]['number']:,}" if kind == "races" else f"<t:{int(pbs[-1]['timestamp'])}:R>"
        description += (
            f"**Best Race:** [{pbs[-1]['wpm']:,.2f} WPM]"
            f"({urls.replay(username, pbs[-1]['number'])}) - "
            f"{indicator}\n"
        )

    embed = Embed(
        title=f"Personal Best Progression",
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats)

    file_name = f"personal_best_over_{kind}_{username}.png"
    graphs.personal_bests(user, username, x, y, kind, file_name)

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    os.remove(file_name)


async def setup(bot):
    await bot.add_cog(PersonalBestGraph(bot))
