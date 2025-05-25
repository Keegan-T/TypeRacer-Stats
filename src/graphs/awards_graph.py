from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta

from graphs.core import plt, color_graph, file_name
from utils import dates


def render(user, username, competitions):
    medal_list = []
    for competition in competitions:
        competitors = sorted(competition["competitors"], key=lambda x: x["points"], reverse=True)
        for i in range(3):
            if competitors[i]["username"] == username:
                medal_list.append({
                    "period": competition["period"],
                    "timestamp": competition["start_time"],
                    "rank": i + 1,
                })
                break

    timestamps = [[], [], []]
    periods = [[], [], []]
    for medal in medal_list:
        rank = medal["rank"]
        period_index = {"day": 1, "week": 2, "month": 3, "year": 4}.get(medal["period"])
        timestamps[rank - 1].append(medal["timestamp"])
        periods[rank - 1].append(period_index)

    fig, ax = plt.subplots()
    ax.scatter(x=timestamps[0], y=periods[0], color="#ffb600", zorder=3)
    ax.scatter(x=timestamps[1], y=periods[1], color="#c0c0c0", zorder=2)
    ax.scatter(x=timestamps[2], y=periods[2], color="#cd7f32", zorder=1)

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

    file = file_name(f"awards_{username}")
    plt.savefig(file)
    plt.close(fig)

    return file
