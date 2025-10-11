from discord.ext import commands

import database.main.races as races
import database.main.users as users
from database.bot.users import get_user
from graphs import personal_best_graph
from utils import errors, urls, strings, dates
from utils.embeds import Page, Message, is_embed

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
        args, user = dates.set_command_date_range(args, user)
        args, user = strings.set_wpm_metric(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, category = result
        await run(ctx, user, username, category)


def get_args(user, args, info):
    params = f"username category:races|time"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, category):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)
    text_pool = user["settings"]["text_pool"]
    wpm_metric = user["settings"]["wpm"]

    column = 2 if category == "time" else 1
    race_list = await races.get_races(
        username, columns=[wpm_metric, "number", "timestamp"], universe=universe,
        start_date=user["start_date"], end_date=user["end_date"],
        text_pool=text_pool,
    )
    if not race_list:
        return await ctx.send(embed=errors.no_races_in_range(universe), content=era_string)
    race_list.sort(key=lambda r: r[column])

    first_race = race_list[0]
    pbs = [first_race]
    wpms = [first_race["wpm"]]
    numbers = [first_race["number"]]
    timestamps = [first_race["timestamp"]]

    for race in race_list:
        wpm, number, timestamp = race
        if wpms[-1] < wpm:
            pbs.append(race)
            wpms.append(wpm)
            numbers.append(number)
            timestamps.append(timestamp)

    def formatter(race, label, time=False):
        indicator = strings.discord_timestamp(race["timestamp"]) if time else f"#{race['number']:,}"
        return (
            f"**{label}:** [{race['wpm']:,.2f} WPM]"
            f"({urls.replay(username, race['number'], universe)}) - {indicator}\n"
        )

    race_description = formatter(first_race, label="First Race")
    time_description = formatter(first_race, label="First Race", time=True)
    latest_break = None

    for i in range(len(pbs) - 1):
        current_pb = pbs[i]["wpm"]
        next_pb = pbs[i + 1]
        next_wpm = next_pb["wpm"]
        next_barrier = next_wpm - (next_wpm % 10)

        if next_barrier > current_pb:
            latest_break = next_pb
            label = "Best Race" if i == len(pbs) - 2 else f"Broke {next_barrier:.0f}"
            race_description += formatter(next_pb, label)
            time_description += formatter(next_pb, label, time=True)

    if latest_break != pbs[-1]:
        race_description += formatter(pbs[-1], "Best Race")
        time_description += formatter(pbs[-1], "Best Race", time=True)

    title = "Personal Best Progression"
    pages = [
        Page(
            title=title,
            description=race_description,
            render=lambda: personal_best_graph.render(user, username, numbers, wpms, "races", universe),
            button_name="Over Races",
            default=category == "races",
        ),
        Page(
            title=title + " (Over Time)",
            description=time_description,
            render=lambda: personal_best_graph.render(user, username, timestamps, wpms, "time", universe),
            button_name="Over Time",
            default=category == "time",
        )
    ]

    message = Message(
        ctx, user, pages,
        profile=stats,
        universe=universe,
        text_pool=text_pool,
        wpm_metric=wpm_metric,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(PersonalBestGraph(bot))
