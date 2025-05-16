from graphs import bar_graph
from graphs.core import plt, color_graph, universe_title, file_name


def render(user, segments, title, universe):
    fig, ax = plt.subplots()
    x = range(1, len(segments) + 1)
    y = []
    raw_y = []
    for segment in segments:
        wpm = segment["wpm"]
        raw_wpm = segment["raw_wpm"]
        if wpm == float("inf"):
            wpm = 0
        if raw_wpm == float("inf"):
            raw_wpm = 0
        y.append(wpm)
        raw_y.append(raw_wpm)

    color = user["colors"]["line"]
    if color in plt.colormaps():
        bar_graph.apply_cmap(ax, user, x, y, raw_y)
    else:
        ax.bar(x, y, color=color)
        ax.bar(x, raw_y, color=user["colors"]["raw"], zorder=0)

    ax.set_ylabel("WPM")
    ax.set_xlabel("Segments")
    plt.grid()
    ax.set_title(universe_title(title, universe))

    color_graph(ax, user)

    file = file_name("segments")
    plt.savefig(file)
    plt.close(fig)

    return file
