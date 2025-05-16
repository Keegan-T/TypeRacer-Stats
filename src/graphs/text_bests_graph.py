from matplotlib.ticker import FuncFormatter

from graphs.core import plt, color_graph, date_x_ticks, interpolate_segments, universe_title, file_name
from utils.strings import format_big_number


def render(user, username, x, y, category, universe):
    fig, ax = plt.subplots()
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
    ax.set_title(universe_title(title, universe))

    if len(y) > 10:
        starts, remaining = y[:10], y[10:]
        if max(starts) > max(remaining):
            ax.set_ylim(top=1.02 * max(remaining))

    color_graph(ax, user)

    category = category.replace(" ", "_")
    file = file_name(f"text_bests_{username}_{category}")
    plt.savefig(file)
    plt.close(fig)

    return file
