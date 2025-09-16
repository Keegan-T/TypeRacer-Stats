import numpy as np

from graphs.core import plt, color_graph, file_name, universe_title


def render(user, title, data, universe="play"):
    x = range(1, len(data) + 1)
    r1_wpm = [pair[0]["wpm"] for pair in data]
    r2_wpm = [pair[1]["wpm"] for pair in data]

    fig, ax = plt.subplots()

    ax.scatter(x, r1_wpm, color="#DD2E44", s=2, label=data[0][0]["username"])
    ax.scatter(x, r2_wpm, color="#55ACEE", s=2, label=data[0][1]["username"])

    if len(x) > 1:
        r1_fit = np.polyfit(x, r1_wpm, 1)
        r2_fit = np.polyfit(x, r2_wpm, 1)

        ax.plot(x, np.polyval(r1_fit, x), color=user["colors"]["graphbackground"], linewidth=3)
        ax.plot(x, np.polyval(r1_fit, x), color="#DD2E44", linewidth=1.5)

        ax.plot(x, np.polyval(r2_fit, x), color=user["colors"]["graphbackground"], linewidth=3)
        ax.plot(x, np.polyval(r2_fit, x), color="#55ACEE", linewidth=1.5)

    ax.set_xlabel("Encounter #")
    ax.set_ylabel("WPM")

    color_graph(ax, user, ignore_line_colors=True)

    ax.set_title(universe_title(title, universe))

    file = file_name("encounters")
    plt.savefig(file)
    plt.close(fig)

    return file
