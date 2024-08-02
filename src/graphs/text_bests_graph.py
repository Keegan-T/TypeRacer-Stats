from matplotlib.ticker import FuncFormatter

from graphs.core import plt, color_graph, date_x_ticks, interpolate_segments
from utils.strings import format_big_number


def render(user, username, x, y, category, file_name, universe):
    ax = plt.subplots()[1]
    x_segments, y_segments = interpolate_segments(x, y)
    ax.plot(x_segments, y_segments)

    if category == "races":
        ax.set_xlabel("Races")
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))
    elif category == "time":
        ax.set_xlabel("Date")
        date_x_ticks(ax, x[0], x[-1])
    else:
        category = "text changes"
        ax.set_xlabel("Text Changes")
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))

    ax.set_ylabel("WPM")
    plt.grid()
    title = f"Text Bests Over {category.title()} - {username}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    ax.set_title(title)

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()
