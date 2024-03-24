from discord import Embed
from discord.ext import commands
import errors
import utils
from database.bot_users import get_user
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from dateutil import parser
from config import prefix
import api.competitions as competitions_api

types = ["day", "week", "month", "year"]
sorts = ["points", "races", "wpm"]
info = {
    "name": "competition",
    "aliases": ["comp", "c", "lastcomp", "lc"],
    "description": "Displays the top 10 users in a competition\n"
                   f"`{prefix}lastcomp` will show the previous competition",
    "parameters": "<type> <date> <sort>",
    "defaults": {
        "type": "day",
        "date": "today",
        "sort": "points",
    },
    "usages": [
        "competition day",
        "competition week 10/24/2022",
        "competition month 6/2022 points",
        "competition year 2023 races",
    ],
    "import": False,
}


class Competition(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def competition(self, ctx, *params):
        user = get_user(ctx)

        kind = "day"
        sort = "points"
        date = datetime.now(tz=timezone.utc)

        # Shorthands
        if len(params) == 1 and utils.get_category(sorts, params[0]):
            return await run(ctx, user, kind, utils.get_category(sorts, params[0]), date)

        if len(params) == 2 and utils.get_category(types, params[0]) and utils.get_category(sorts, params[1]):
            return await run(ctx, user, utils.get_category(types, params[0]),
                             utils.get_category(sorts, params[1]), date)

        if len(params) > 0:
            kind = utils.get_category(types, params[0])
            if not kind:
                return await ctx.send(embed=errors.invalid_option("type", types))

        if len(params) > 1:
            date_string = params[1]
            try:
                date = parser.parse(date_string)
            except ValueError:
                return await ctx.send(embed=errors.invalid_date())

        if len(params) > 2:
            sort = utils.get_category(sorts, params[2])
            if not sort:
                return await ctx.send(embed=errors.invalid_option("sort", sorts))

        await run(ctx, user, kind, sort, date)


async def run(ctx, user, kind, sort, date):
    sort_title = ""
    if sort == "races":
        sort_title = "(By Races) "
    elif sort == "wpm":
        sort_title = "(By WPM) "

    now = utils.now()

    if kind == "week":
        if ctx.invoked_with in ["lastcomp", "lc"]:
            date -= relativedelta(days=7)
        start_date = utils.floor_week(date)
        end_date = start_date + relativedelta(days=7)
        date_string = utils.get_display_date_range(start_date, (end_date - relativedelta(days=1)))
        title = f"Weekly Competition {sort_title}- {date_string}"

        next_comp_start = utils.floor_week(now + relativedelta(days=7))
        requested_comp_start = start_date

    elif kind == "month":
        if ctx.invoked_with in ["lastcomp", "lc"]:
            date -= relativedelta(months=1)
        date_string = date.strftime("%B %Y")
        title = f"Monthly Competition {sort_title}- {date_string}"

        next_comp_start = utils.floor_month(now + relativedelta(months=1))
        requested_comp_start = utils.floor_month(date)


    elif kind == "year":
        if ctx.invoked_with in ["lastcomp", "lc"]:
            date -= relativedelta(years=1)
        date_string = date.year
        title = f"Yearly Competition {sort_title}- {date_string}"

        next_comp_start = utils.floor_year(now + relativedelta(years=1))
        requested_comp_start = utils.floor_year(date)

    else:
        if ctx.invoked_with in ["lastcomp", "lc"]:
            date -= relativedelta(days=1)
        title = f"Daily Competition {sort_title}- {utils.get_display_date(date)}"

        next_comp_start = utils.floor_day(now + relativedelta(days=1))
        requested_comp_start = utils.floor_day(date)

    if requested_comp_start >= next_comp_start:
        return await competition_not_started(ctx, title, user, requested_comp_start)


    competition = competitions_api.get_competition_info(date, kind, sort, 10)
    date_string = date.strftime("%Y-%m-%d")
    competition_url = f"https://data.typeracer.com/pit/competitions?date={date_string}&sort={sort}&kind={kind}"
    if not competition:
        embed = Embed(
            title=title,
            description="No results found.",
            url=competition_url,
            color=user["colors"]["embed"],
        )
        embed.set_footer(text="Competitions started July 27th, 2017")

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

# Different formatted version (columns aligned in code block)
# description = ""
#
# max_len = {"username": 0, "points": 0, "races": 5}
#
# for i, competitor in enumerate(competition):
#     max_len['username'] = max(max_len['username'], len(competitor['username']))
#     max_len['points'] = max(max_len['points'], len(f"{competitor['points']:,}"))
#     max_len['races'] = max(max_len['races'], len(f"{competitor['races']:,}"))
#
# description += (
#         "    " +
#         "Username".ljust(max_len["username"]) + " | " +
#         "Points".ljust(max_len["points"]) + " | " +
#         "Races".ljust(max_len["races"]) + " | " +
#         "Average".ljust(9) + " | " +
#         "Acc.\n"
# )
#
# for i, competitor in enumerate(competition):
#     rank = i + 1
#
#     description += (
#             f"{rank}. ".rjust(4) +
#             f"{competitor['username']}".ljust(max_len['username']) + " | " +
#             f"{competitor['points']:,}".rjust(max_len['points']) + " | " +
#             f"{competitor['races']:,}".rjust(max_len['races']) + " | " +
#             f"{competitor['average_wpm']} WPM".rjust(9) + " | " +
#             f"{competitor['accuracy'] * 100:,.1f}%\n"
#     )