from collections import defaultdict

import numpy as np

from graphs.core import plt, color_graph


def render(user, rankings, title, y_label, file_name, limit_y=True, typos=[], markers=[]):
    ax = plt.subplots()[1]
    caller_index = 0
    starts = []
    remaining = []
    inf = float("inf")
    min_wpm = inf
    max_wpm = 0

    if "average_adjusted_wpm" in rankings[0]:
        racer = rankings[0]
        instant_chars = racer["instant_chars"]
        average_wpm = racer["average_adjusted_wpm"][instant_chars:]
        keystrokes = np.arange(instant_chars + 1, len(average_wpm) + instant_chars + 1)
        ax.plot(keystrokes, average_wpm)
        min_wpm = min(min_wpm, min(average_wpm))
        non_inf_values = [wpm for wpm in average_wpm if wpm < inf]
        if non_inf_values:
            max_wpm = max(max_wpm, max(non_inf_values))
        starts += average_wpm[:9]
        remaining += average_wpm[9:]

    else:
        caller = user["username"]
        for i, racer in enumerate(rankings):
            zorder = len(rankings) + 5 - i
            racer_username = racer["username"]
            if racer_username in [caller, "Adjusted"]:
                caller_index = i
                zorder *= 10
            average_wpm = racer["average_wpm"]
            keystrokes = np.arange(1, len(average_wpm) + 1)
            ax.plot(keystrokes, average_wpm, label=racer_username, zorder=zorder)
            min_wpm = min(min_wpm, min(average_wpm))
            non_inf_values = [wpm for wpm in average_wpm if wpm < inf]
            if non_inf_values:
                max_wpm = max(max_wpm, max(non_inf_values))
            starts += average_wpm[:9]
            remaining += average_wpm[9:]

    if remaining and limit_y:
        if max(starts) > max(remaining):
            max_wpm = max(remaining) * 1.1
        if min(starts) < min(remaining):
            min_wpm = min(remaining) * 0.9

    if min_wpm < inf:
        padding = 0.1 * (max_wpm - min_wpm)
        ax.set_ylim(bottom=min_wpm - padding)
        ax.set_ylim(top=max_wpm + padding)

    if typos:
        word_counts = defaultdict(int)
        for word_index, _, _ in typos:
            word_counts[word_index] += 1

        typo_count = 0
        word_indexes = {}

        for word_index, index, word in typos:
            last_index = word_indexes.get(word_index, -1)
            if index <= last_index:
                continue

            word_indexes[word_index] = index
            wpm = rankings[0]["average_wpm"][max(0, index - 1)]

            label = None
            if last_index == -1:
                typo_count += 1
                label = f"{typo_count}. {word}"
                if word_counts[word_index] > 1:
                    label += f" (x{word_counts[word_index]})"

            ax.plot(
                index, wpm, marker="x", color="red", zorder=999, markersize=7,
                markeredgewidth=1.5, label=label
            )

    if markers:
        typos, pauses = markers
        typos = [typo[1] for typo in typos]

        if typos:
            x = typos
            y = [rankings[1]["average_wpm"][max(0, i - 1)] for i in x]
            ax.plot(x, y, marker=".", linestyle="None", zorder=999, markersize=7, color="red", label="Corrections")

        if pauses:
            x = pauses
            y = [rankings[1]["average_wpm"][max(0, i - 1)] for i in x]
            ax.plot(x, y, marker=".", linestyle="None", zorder=888, markersize=7, color="#ffb600", label="Pauses")

    ax.set_xlabel("Keystrokes")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid()

    color_graph(ax, user, caller_index, match=True)

    plt.savefig(file_name)
    plt.close()
