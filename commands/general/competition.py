from discord import Embed
from discord.ext import commands
import utils
import errors
from database.bot_users import get_user
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from dateutil import parser
from config import prefix
import api.competitions as competitions_api

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
        if len(args) == 1 and utils.get_category(sorts, args[0]):
            return await run(ctx, user, period, utils.get_category(sorts, args[0]), date)

        # -comp day races
        if len(args) == 2 and utils.get_category(periods, args[0]) and utils.get_category(sorts, args[1]):
            return await run(ctx, user, utils.get_category(periods, args[0]),
                             utils.get_category(sorts, args[1]), date)

        if len(args) > 0:
            period = utils.get_category(periods, args[0])
            if not period:
                return await ctx.send(embed=errors.invalid_choice("period", periods))

        if len(args) > 1:
            date_string = args[1]
            try:
                date = parser.parse(date_string)
            except ValueError:
                return await ctx.send(embed=errors.invalid_date())

        if len(args) > 2:
            sort = utils.get_category(sorts, args[2])
            if not sort:
                return await ctx.send(embed=errors.invalid_choice("sort", sorts))

        await run(ctx, user, period, sort, date)


async def run(ctx, user, period, sort, date):
    universe = user["universe"]
    now = utils.now()
    previous = ctx.invoked_with.lower() in ["lastcomp", "lc"]

    if period == "week":
        if previous:
            date -= relativedelta(weeks=1)
        start_date = utils.floor_week(date)
        end_date = start_date + relativedelta(weeks=1)
        date_string = utils.get_display_date_range(start_date, (end_date - relativedelta(days=1)))
        title = "Weekly"

        next_comp_start = utils.floor_week(now + relativedelta(weeks=1))
        requested_comp_start = start_date

    elif period == "month":
        if previous:
            date -= relativedelta(months=1)
        date_string = date.strftime("%B %Y")
        title = "Monthly"

        next_comp_start = utils.floor_month(now + relativedelta(months=1))
        requested_comp_start = utils.floor_month(date)


    elif period == "year":
        if previous:
            date -= relativedelta(years=1)
        date_string = date.year
        title = "Yearly"

        next_comp_start = utils.floor_year(now + relativedelta(years=1))
        requested_comp_start = utils.floor_year(date)

    else:
        if previous:
            date -= relativedelta(days=1)
        date_string = utils.get_display_date(date)
        title = "Daily"

        next_comp_start = utils.floor_day(now + relativedelta(days=1))
        requested_comp_start = utils.floor_day(date)

    if requested_comp_start >= next_comp_start:
        return await competition_not_started(ctx, title, user, requested_comp_start)

    title += " Competition"
    if sort == "races":
        title += " (By Races)"
    elif sort == "wpm":
        title += " (By WPM)"
    title += f" - {date_string}"

    competition = await competitions_api.get_competition_info(date, period, sort, 10, universe)
    date_string = date.strftime("%Y-%m-%d")
    competition_url = (f"https://data.typeracer.com/pit/competitions?date={date_string}"
                       f"&sort={sort}&kind={period}&universe={universe}")
    if not competition:
        embed = Embed(
            title=title,
            description="No results found.",
            url=competition_url,
            color=user["colors"]["embed"],
        )
        embed.set_footer(text="Competitions started July 27th, 2017")
        utils.add_universe(embed, universe)

        return await ctx.send(embed=embed)

    description = ""

    for i, competitor in enumerate(competition["competitors"]):
        rank = utils.rank(i + 1)
        username = competitor['username']
        bold = "**" if username == user["username"] else ""
        flag = "" if not competitor["country"] else f":flag_{competitor['country']}:"
        description += (
            f"{rank} {bold}{flag} {utils.escape_discord_format(username)} - {competitor['points']:,} / "
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
    utils.add_universe(embed, universe)

    await ctx.send(embed=embed)


async def competition_not_started(ctx, title, user, start):
    await ctx.send(embed=Embed(
        title=title,
        description="No results found.\n\n"
                    f"Starts {utils.discord_timestamp(start.timestamp())}",
        color=user["colors"]["embed"],
    ))


async def setup(bot):
    await bot.add_cog(Competition(bot))
