import numpy as np
from matplotlib.colors import hex2color
from matplotlib.ticker import FuncFormatter

from graphs.core import plt, color_graph, date_x_ticks, interpolate_segments, file_name
from utils.strings import format_big_number


def render(user, wpm, title, timeframe="", timestamps=None, universe="play"):
    text_graph = "Text #" in title
    wpm = np.array(wpm)
    best_index, best = max(enumerate(wpm), key=lambda x: x[1])
    worst_index, worst = min(enumerate(wpm), key=lambda x: x[1])

    fig, ax = plt.subplots()

    downsample_factor = max(len(wpm) // 100000, 1)
    downsampled_indices = np.arange(0, len(wpm), downsample_factor)
    downsampled_wpm = wpm[downsampled_indices]

    max_window = 50 if text_graph else 500
    window_size = min(max(len(wpm) // 15, 1), max_window)

    if len(wpm) > 10000:
        downsample_factor *= 10

    moving_wpm = np.convolve(wpm, np.ones(window_size) / window_size, mode="valid")[0::downsample_factor]
    x_points = np.arange(window_size - 1, len(wpm))[0::downsample_factor]

    if timestamps:
        timestamps = np.array(timestamps)
        downsampled_indices = [timestamps[d] for d in downsampled_indices]
        x_points = [timestamps[r] for r in x_points]
        ax.scatter(timestamps[worst_index], worst, color="#FA3244", marker=".", zorder=10)
        ax.scatter(timestamps[best_index], best, color="#53D76A", marker=".", zorder=10)
        date_x_ticks(ax, min(timestamps), max(timestamps))

    else:
        downsampled_indices = [d + 1 for d in downsampled_indices]
        x_points = [r + 1 for r in x_points]
        ax.scatter(worst_index + 1, worst, color="#FA3244", marker=".", zorder=10)
        ax.scatter(best_index + 1, best, color="#53D76A", marker=".", zorder=10)
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))

    bg_color = hex2color(user["colors"]["graphbackground"])
    point_color = "white" if np.mean(bg_color) < 0.5 else "black"

    ax.scatter(downsampled_indices, downsampled_wpm, alpha=0.1, s=25, color=point_color, edgecolors="none")

    segment_count = 50 // (len(moving_wpm) - 1) if len(moving_wpm) > 1 else 1
    if segment_count > 1:
        x_segments, y_segments = interpolate_segments(x_points, moving_wpm)
        ax.plot(x_segments, y_segments)
    else:
        ax.plot(x_points, moving_wpm)

    ax.set_xlabel(f"Races{timeframe}")
    ax.set_ylabel(["Performance", "WPM"]["WPM" in title])
    if window_size > 1:
        title += f"\nMoving Average of {window_size} Races"
    if universe != "play":
        separator = " | " if "\n" in title else "\n"
        title += f"{separator}Universe: {universe}"
    ax.set_title(title)
    ax.grid()

    color_graph(ax, user)

    file = file_name("improvement")
    plt.savefig(file)
    plt.close(fig)

    return file
