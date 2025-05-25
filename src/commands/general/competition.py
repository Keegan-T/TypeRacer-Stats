from datetime import datetime, timezone

from dateutil import parser
from dateutil.relativedelta import relativedelta
from discord import Embed
from discord.ext import commands

import api.competitions as competitions_api
from config import prefix
from database.bot.users import get_user
from utils import errors, strings, dates, embeds, urls

periods = ["day", "week", "month", "year"]
sorts = ["points", "races", "wpm"]
command = {
    "name": "competition",
    "aliases": ["comp", "c", "lastcomp", "lc"],
    "description": "Displays the top 10 users in a competition\n"
                   f"`{prefix}lastcomp` will show the previous competition",
    "parameters": "<period> <date> <sort>",
    "defaults": {
        "period": "day",
        "date": "today",
        "sort": "points",
    },
    "usages": [
        "competition day",
        "competition week 10/24/2022",
        "competition month 6/2022 points",
        "competition year 2023 races",
    ],
}


class Competition(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def competition(self, ctx, *args):
        user = get_user(ctx)

        period = "day"
        sort = "points"
        date = datetime.now(tz=timezone.utc)

        # Shorthands
        # -comp races
        if len(args) == 1 and strings.get_category(sorts, args[0]):
            return await run(ctx, user, period, strings.get_category(sorts, args[0]), date)

        # -comp day races
        if len(args) == 2 and strings.get_category(periods, args[0]) and strings.get_category(sorts, args[1]):
            return await run(ctx, user, strings.get_category(periods, args[0]),
                             strings.get_category(sorts, args[1]), date)

        if len(args) > 0:
            period = strings.get_category(periods, args[0])
            if not period:
                return await ctx.send(embed=errors.invalid_choice("period", periods))

        if len(args) > 1:
            date_string = args[1]
            try:
                date = parser.parse(date_string)
            except ValueError:
                return await ctx.send(embed=errors.invalid_date())

        if len(args) > 2:
            sort = strings.get_category(sorts, args[2])
            if not sort:
                return await ctx.send(embed=errors.invalid_choice("sort", sorts))

        await run(ctx, user, period, sort, date)


async def run(ctx, user, period, sort, date):
    universe = user["universe"]
    now = dates.now()
    previous = ctx.invoked_with.lower() in ["lastcomp", "lc"]

    if period == "week":
        if previous:
            date -= relativedelta(weeks=1)
        start_date = dates.floor_week(date)
        end_date = start_date + relativedelta(weeks=1)
        date_string = strings.get_display_date_range(start_date, (end_date - relativedelta(days=1)))
        title = "Weekly"

        next_comp_start = dates.floor_week(now + relativedelta(weeks=1))
        requested_comp_start = start_date

    elif period == "month":
        if previous:
            date -= relativedelta(months=1)
        date_string = date.strftime("%B %Y")
        title = "Monthly"

        next_comp_start = dates.floor_month(now + relativedelta(months=1))
        requested_comp_start = dates.floor_month(date)

    elif period == "year":
        if previous:
            date -= relativedelta(years=1)
        date_string = date.year
        title = "Yearly"

        next_comp_start = dates.floor_year(now + relativedelta(years=1))
        requested_comp_start = dates.floor_year(date)

    else:
        if previous:
            date -= relativedelta(days=1)
        date_string = strings.get_display_date(date)
        title = "Daily"

        next_comp_start = dates.floor_day(now + relativedelta(days=1))
        requested_comp_start = dates.floor_day(date)

    if requested_comp_start >= next_comp_start:
        return await competition_not_started(ctx, title, user, requested_comp_start)

    title += " Competition"
    if sort == "races":
        title += " (By Races)"
    elif sort == "wpm":
        title += " (By WPM)"
    title += f" - {date_string}"

    competition = await competitions_api.get_competition_info(date, period, sort, 10, universe)
    competition_url = urls.competition(date, period, sort, 10, universe)

    if not competition:
        embed = Embed(
            title=title,
            description="No results found.",
            url=competition_url,
            color=user["colors"]["embed"],
        )
        embed.set_footer(text="Competitions started July 27th, 2017")
        embeds.add_universe(embed, universe)

        return await ctx.send(embed=embed)

    description = ""

    for i, competitor in enumerate(competition["competitors"]):
        rank = strings.rank(i + 1)
        username = competitor['username']
        bold = "**" if username == user["username"] else ""
        flag = "" if not competitor["country"] else f":flag_{competitor['country']}:"
        description += (
            f"{rank} {bold}{flag} {strings.escape_formatting(username)} - {competitor['points']:,} / "
            f"{competitor['races']:,} - {competitor['average_wpm']} WPM "
            f"({competitor['accuracy'] * 100:,.1f}% Acc){bold}\n"
        )

    end_timestamp = competition["end_timestamp"]
    now = datetime.now(tz=timezone.utc).timestamp()

    end_string = "Ends "
    if end_timestamp < now:
        end_string = "Ended "
    description += f"\n{end_string} <t:{int(end_timestamp)}:R>\n"

    embed = Embed(
        title=title,
        description=description,
        url=competition_url,
        color=user["colors"]["embed"],
    )
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


async def competition_not_started(ctx, title, user, start):
    await ctx.send(embed=Embed(
        title=title,
        description="No results found.\n\n"
                    f"Starts {strings.discord_timestamp(start.timestamp())}",
        color=user["colors"]["embed"],
    ))


async def setup(bot):
    await bot.add_cog(Competition(bot))
