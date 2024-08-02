import numpy as np
from matplotlib.colors import hex2color
from matplotlib.ticker import FuncFormatter

from graphs.core import plt, color_graph, date_x_ticks, interpolate_segments
from utils.strings import format_big_number


def render(user, username, x, y, category, file_name, universe):
    ax = plt.subplots()[1]

    x_segments, y_segments = interpolate_segments(x, y)
    ax.plot(x_segments, y_segments)

    bg_color = hex2color(user["colors"]["graphbackground"])
    point_color = "white" if np.mean(bg_color) < 0.5 else "black"
    ax.scatter(x, y, alpha=0.5, s=25, color=point_color, edgecolors="none")

    if category == "races":
        ax.set_xlabel("Races")
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))
    else:
        ax.set_xlabel("Date")
        date_x_ticks(ax, x[0], x[-1])

    ax.set_ylabel("WPM")
    plt.grid()
    title = f"Personal Best Over {category.title()} - {username}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    ax.set_title(title)

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()
