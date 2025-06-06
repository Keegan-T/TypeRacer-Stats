import numpy as np
from matplotlib.ticker import FuncFormatter

from graphs.core import plt, color_graph, universe_title, file_name
from utils.strings import format_big_number


def render(user, username, values, category, y_label, bins, universe):
    fig, ax = plt.subplots()
    counts, groups = np.histogram(values, bins=bins)

    color = user["colors"]["line"]

    if color in plt.colormaps():
        apply_cmap(ax, user, counts, groups)
    else:
        ax.bar(groups[:-1], counts, width=np.diff(groups), align="edge", color=color)

    if category == "Accuracy":
        x_ticks = ax.get_xticks()
        ax.set_xticks(x_ticks + 0.5, [int(value) for value in x_ticks])
        ax.set_xlim(max(ax.get_xlim()[0], 90), 101)

    ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))
    ax.set_xlabel(y_label)
    ax.set_ylabel("Frequency")
    title = universe_title(f"{category} Histogram - {username}", universe)
    ax.set_title(title)
    ax.grid()

    color_graph(ax, user)

    category = category.replace(" ", "_")
    file = file_name(f"{category.lower()}_histogram_{username}")
    plt.savefig(file)
    plt.close(fig)

    return file


def apply_cmap(ax, user, counts, groups):
    cmap = plt.get_cmap(user["colors"]["line"])

    mask = np.zeros((len(groups), 2))
    mask[:, 0] = np.concatenate([groups[:-1], [groups[-1]]])
    mask[:-1, 1] = counts

    ax.bar(groups[:-1], counts, width=np.diff(groups), align="edge", alpha=0)
    original_ylim = ax.get_ylim()

    extent = [ax.get_xlim()[0], ax.get_xlim()[1], 0, max(counts)]

    x = np.linspace(0, 10, 100)
    y = np.linspace(0, 10, 100)
    X, Y = np.meshgrid(x, y)

    ax.imshow(Y, cmap=cmap, extent=extent, origin="lower", aspect="auto")
    ax.set_ylim(original_ylim)

    graph_background = user["colors"]["graphbackground"]
    ax.fill_between(mask[:, 0], mask[:, 1], extent[3], color=graph_background, step="post")
    ax.fill_between([extent[0], groups[0]], [0, 0], [extent[3], extent[3]], color=graph_background)
    ax.fill_between([groups[-1], extent[1]], [0, 0], [extent[3], extent[3]], color=graph_background)
