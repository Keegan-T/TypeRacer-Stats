import numpy as np
from matplotlib import patches
from matplotlib.ticker import FuncFormatter

from graphs.core import plt, color_graph, universe_title
from utils.strings import format_big_number


def render(user, username, activity, file_name, universe):
    ax = plt.subplots()[1]
    days = range(len(activity))

    color = user["colors"]["line"]
    if color in plt.colormaps():
        apply_cmap(ax, user, days, activity)
    else:
        ax.bar(days, activity, color=color)

    ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))
    ax.set_ylabel("Races")
    ax.set_xticks(days)
    ax.set_xticklabels(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
    title = f"Weekly Activity - {username}"
    ax.set_title(universe_title(title, universe))

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()


def apply_cmap(ax, user, labels, values, top_values=None):
    cmap = plt.get_cmap(user["colors"]["line"])

    bars = ax.bar(labels, values, alpha=0)
    original_ylim = ax.get_ylim()

    extent = [ax.get_xlim()[0], ax.get_xlim()[1], 0, max(values)]

    x = np.linspace(0, 10, 100)
    y = np.linspace(0, 10, 100)
    X, Y = np.meshgrid(x, y)

    ax.imshow(Y, cmap=cmap, extent=extent, origin="lower", aspect="auto")
    ax.set_ylim(original_ylim)

    graph_background = user["colors"]["graphbackground"]
    bar_width = bars[0].get_width()

    max_y = max(values)
    if top_values:
        values = top_values
        for i, bar in enumerate(bars):
            target_y_value = values[i]
            bar_height = bar.get_height()
            bar_left = bar.get_x()
            if bar_height < target_y_value:
                if target_y_value > max_y:
                    max_y = target_y_value
                rect = patches.Rectangle(
                    (bar_left, bar_height),
                    bar_width,
                    target_y_value - bar_height,
                    color=user["colors"]["raw"]
                )
                ax.add_patch(rect)

    if original_ylim[1] < max_y:
        ax.set_ylim(top=max_y * 1.05)
        original_ylim = (0.0, max_y * 1.05)

    for i in range(len(labels) - 1):
        left = labels[i] + bar_width / 2
        right = labels[i + 1] - bar_width / 2
        rect = patches.Rectangle(
            (left, 0),
            right - left, original_ylim[1],
            color=graph_background
        )
        ax.add_patch(rect)

    bars = ax.bar(labels, values, alpha=0)
    for bar in bars:
        bar_height = bar.get_height()
        bar_left = bar.get_x()
        rect = patches.Rectangle(
            (bar_left, bar_height), bar_width,
            original_ylim[1] - bar_height,
            color=graph_background
        )
        ax.add_patch(rect)

    left_padding = ax.get_xlim()[0]
    right_padding = ax.get_xlim()[1]

    rect_left = patches.Rectangle(
        (left_padding, 0),
        labels[0] - bar_width / 2 - left_padding,
        original_ylim[1], color=graph_background
    )
    ax.add_patch(rect_left)

    rect_right = patches.Rectangle(
        (labels[-1] + bar_width / 2, 0),
        right_padding - (labels[-1] + bar_width / 2),
        original_ylim[1], color=graph_background
    )
    ax.add_patch(rect_right)
