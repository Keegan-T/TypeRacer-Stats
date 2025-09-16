from graphs.core import plt, color_graph, file_name, universe_title


def render(user, title, data, universe="play"):
    x = range(1, len(data) + 1)
    r1_wpm = [pair[0]["wpm"] for pair in data]
    r2_wpm = [pair[1]["wpm"] for pair in data]

    fig, ax = plt.subplots()

    ax.scatter(x, r1_wpm, color="#DD2E44", s=2, label=data[0][0]["username"])
    ax.scatter(x, r2_wpm, color="#55ACEE", s=2, label=data[0][1]["username"])

    ax.set_xlabel("Encounter #")
    ax.set_ylabel("WPM")

    color_graph(ax, user)

    ax.set_title(universe_title(title, universe))

    file = file_name("encounters")
    plt.savefig(file)
    plt.close(fig)

    return file
