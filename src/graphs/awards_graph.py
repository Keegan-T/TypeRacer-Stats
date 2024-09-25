from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta

from database.competition_results import get_competitions
from graphs.core import plt, color_graph
from utils import dates


async def render(user, username, file_name):
    medal_list = []
    competitions = list(await get_competitions())
    competitions.sort(key=lambda x: x["end_time"])

    for competition in competitions:
        competitors = sorted(competition["competitors"], key=lambda x: x["points"], reverse=True)
        for i in range(3):
            if competitors[i]["username"] == username:
                medal_list.append({
                    "type": competition["type"],
                    "timestamp": competition["start_time"],
                    "rank": i + 1,
                })
                break

    timestamps = [[], [], []]
    types = [[], [], []]
    for medal in medal_list:
        rank = medal["rank"]
        type_index = {"day": 1, "week": 2, "month": 3, "year": 4}.get(medal["type"])
        timestamps[rank - 1].append(medal["timestamp"])
        types[rank - 1].append(type_index)

    ax = plt.subplots()[1]
    ax.scatter(x=timestamps[0], y=types[0], color="#ffb600", zorder=3)
    ax.scatter(x=timestamps[1], y=types[1], color="#c0c0c0", zorder=2)
    ax.scatter(x=timestamps[2], y=types[2], color="#cd7f32", zorder=1)

    first_year = datetime.fromtimestamp(1514764800).astimezone(timezone.utc)
    now = dates.floor_day(dates.now())

    x_ticks = []
    year = first_year
    while year < now:
        x_ticks.append(year)
        year += relativedelta(years=1)

    ax.set_xticks([date.timestamp() for date in x_ticks])
    ax.set_xticklabels([date.year for date in x_ticks])
    ax.set_xlim(medal_list[0]["timestamp"], now.timestamp())

    ax.set_yticks([4, 3, 2, 1])
    ax.set_yticklabels(["Year", "Month", "Week", "Day"])
    ax.set_title(f"Awards Graph - {username}")
    ax.xaxis.grid()

    color_graph(ax, user)

    plt.savefig(file_name)
