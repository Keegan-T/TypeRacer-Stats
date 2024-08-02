from matplotlib.ticker import FuncFormatter

from graphs.core import plt, color_graph, interpolate_segments, date_x_ticks
from utils.strings import format_big_number


def render(user, lines, title, x_label, y_label, file_name):
    ax = plt.subplots()[1]

    caller = user["username"]
    caller_index = 0
    for i, l in enumerate(lines):
        username, x, y = l[:3]
        first_x, first_y = x[0], y[0]
        last_x, last_y = x[-1], y[-1]
        if len(x) > 10000:
            x = x[::len(x) // 1000]
            y = y[::len(y) // 1000]
        x.insert(0, first_x)
        x.append(last_x)
        y.insert(0, first_y)
        y.append(last_y)

        x, y = interpolate_segments(x, y)
        ax.plot(x, y, label=username)

        if username == caller:
            caller_index = i

    plt.grid()
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    min_timestamp = min(min(l[1]) for l in lines)
    max_timestamp = max(max(l[1]) for l in lines)
    date_x_ticks(ax, min_timestamp, max_timestamp)

    ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))

    color_graph(ax, user, caller_index)

    plt.savefig(file_name)
    plt.close()
