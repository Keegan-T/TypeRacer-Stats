import numpy as np

from graphs.core import plt, color_graph, file_name


def render(user, user1, user2):
    username1, data1 = user1
    username2, data2 = user2
    fig, (ax1, ax2) = plt.subplots(1, 2)

    color = user["colors"]["line"]
    counts1, groups1 = np.histogram(data1, bins="auto")
    counts2, groups2 = np.histogram(data2, bins="auto")

    if color in plt.colormaps():
        ax1.hist(data1, bins="auto", orientation="horizontal", alpha=0)
        ax2.hist(data2, bins="auto", orientation="horizontal", alpha=0)
    else:
        ax1.hist(data1, bins="auto", orientation="horizontal", color=color)
        ax2.hist(data2, bins="auto", orientation="horizontal", color=color)

    ax1.set_ylabel("WPM Difference")
    ax2.yaxis.tick_right()

    max_xlim = max(ax1.get_xlim()[1], ax2.get_xlim()[1])
    ax2.set_xlim(0, max_xlim)
    ax1.set_xlim(ax2.get_xlim()[::-1])

    min_ylim = min(ax1.get_ylim()[0], ax2.get_ylim()[0])
    max_ylim = max(ax1.get_ylim()[1], ax2.get_ylim()[1])
    ax1.set_ylim(min_ylim, max_ylim)
    ax2.set_ylim(min_ylim, max_ylim)

    if color in plt.colormaps():
        apply_cmap(ax1, user, counts1, groups1, [0, max(counts1), min_ylim, max_ylim])
        apply_cmap(ax2, user, counts2, groups2, [0, max(counts2), min_ylim, max_ylim])

    ax1.grid()
    ax1.set_title(username1)

    ax2.grid()
    ax2.set_title(username2)

    color_graph(ax1, user)
    color_graph(ax2, user)

    plt.subplots_adjust(wspace=0, hspace=0)

    fig.suptitle(f"Text Bests Comparison", color=user["colors"]["text"])
    fig.text(0.5, 0.025, "Number of Texts", ha="center", color=user["colors"]["text"])

    file = file_name(f"compare_{username1}_{username2}")
    plt.savefig(file)
    plt.close(fig)

    return file


def apply_cmap(ax, user, counts, groups, extent):
    cmap = plt.get_cmap(user["colors"]["line"])

    mask = np.zeros((len(groups), 2))
    mask[:, 0] = np.concatenate([groups[:-1], [groups[-1]]])
    mask[:-1, 1] = counts

    ax.barh(groups[:-1], counts, height=np.diff(groups), align="edge", alpha=0)
    original_xlim = ax.get_xlim()

    x = np.linspace(0, 10, 100)
    y = np.linspace(0, 10, 100)
    X, Y = np.meshgrid(x, y)

    ax.imshow(X, cmap=cmap, extent=extent, origin="lower", aspect="auto")
    ax.set_xlim(original_xlim)

    graph_background = user["colors"]["graphbackground"]
    ax.fill_betweenx(mask[:, 0], mask[:, 1], extent[1], color=graph_background, step='post')
    ax.fill_betweenx([extent[2], groups[0]], [0, 0], [extent[1], extent[1]], color=graph_background)
    ax.fill_betweenx([groups[-1], extent[3]], [0, 0], [extent[1], extent[1]], color=graph_background)
