import numpy as np

from graphs.core import plt, color_graph, file_name, universe_title


def moving_average(y, window=20):
    if len(y) < window:
        return y
    return np.convolve(y, np.ones(window) / window, mode="valid")


def render(user, title, data, universe="play"):
    x = range(1, len(data) + 1)
    r1_wpm = [pair[0]["wpm"] for pair in data]
    r2_wpm = [pair[1]["wpm"] for pair in data]

    fig, ax = plt.subplots()

    ax.scatter(x, r2_wpm, color="#55ACEE", s=2, label=data[0][1]["username"])
    ax.scatter(x, r1_wpm, color="#DD2E44", s=2, label=data[0][0]["username"])

    if len(x) > 1:
        window = max(5, len(x) // 20)

        r1_avg = moving_average(r1_wpm, window)
        r2_avg = moving_average(r2_wpm, window)

        x_avg = range(window, len(x) + 1)

        ax.plot(x_avg, r2_avg, color=user["colors"]["graphbackground"], linewidth=4)
        ax.plot(x_avg, r2_avg, color="#55ACEE", linewidth=1.5)

        ax.plot(x_avg, r1_avg, color=user["colors"]["graphbackground"], linewidth=4)
        ax.plot(x_avg, r1_avg, color="#DD2E44", linewidth=1.5)

    ax.set_xlabel("Encounter #")
    ax.set_ylabel("WPM")

    color_graph(ax, user, ignore_line_colors=True)

    ax.set_title(universe_title(title, universe))

    file = file_name("encounters")
    plt.savefig(file)
    plt.close(fig)

    return file
