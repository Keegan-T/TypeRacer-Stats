from datetime import datetime, timezone
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, hex2color
from matplotlib.legend_handler import HandlerLineCollection
from matplotlib.legend_handler import HandlerLine2D
from matplotlib.ticker import FuncFormatter, MaxNLocator, FixedLocator
from matplotlib import rcParams
import numpy as np
from utils import format_big_number
from config import bot_owner

rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["Exo 2"]
rcParams["font.size"] = 11
cmap_keegant = LinearSegmentedColormap.from_list('keegant', ["#0094FF", "#FF00DC"])

class LineHandler(HandlerLine2D):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        line = plt.Line2D([0, 21], [3.5, 3.5], color=orig_handle.get_color())
        return [line]


class CollectionHandler(HandlerLineCollection):
    def create_artists(self, legend, artist, xdescent, ydescent, width, height, fontsize, trans):
        x = np.linspace(0, width, self.get_numpoints(legend) + 1)
        y = np.zeros(self.get_numpoints(legend) + 1) + height / 2. - ydescent
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc = LineCollection(segments, cmap=artist.cmap, transform=trans)
        lc.set_array(x)
        return [lc]

def get_cmap(user):
    cmap = plt.get_cmap(user["colors"]["line"])
    if int(user["id"]) == bot_owner and cmap.name == "cool":
        cmap = cmap_keegant

    return cmap

def date_x_ticks(ax, min_timestamp, max_timestamp):
    date_range = max_timestamp - min_timestamp
    step = date_range / 5

    ticks = [min_timestamp + step * i for i in range(6)]
    # labels = [datetime.fromtimestamp(ts, timezone.utc).strftime("%#m/%#d/%y") for ts in ticks]
    labels = [datetime.fromtimestamp(ts, timezone.utc).strftime("%b %#d '%y") for ts in ticks]

    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)

    padding = date_range * 0.05
    ax.set_xlim(min_timestamp - padding, max_timestamp + padding)


def get_interpolated_segments(x, y):
    x_segments = []
    y_segments = []

    for i in range(len(y) - 1):
        x_range = x[-1] - x[0]
        x_difference = x[i + 1] - x[i]
        if x_difference == 0:
            continue
        x_size = x_range / x_difference
        segment_count = max(int(50 / x_size), 2)
        if segment_count == 2 and i < len(y) - 2:
            x_segments.append(x[i])
            y_segments.append(y[i])
            continue

        segments = np.linspace(y[i], y[i + 1], segment_count)
        for v in segments[:-1]:
            y_segments.append(v)

        segments = np.linspace(x[i], x[i + 1], segment_count)
        for v in segments[:-1]:
            x_segments.append(v)

    y_segments.append(y[-1])
    x_segments.append(x[-1])

    return x_segments, y_segments


def cmap_line(ax, line_index, user):
    line_width = 1
    cmap = get_cmap(user)
    if int(user["id"]) == bot_owner:
        line_width = 2

    line = ax.get_lines()[line_index]
    x, y = line.get_data()
    ax.lines.pop(line_index)

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap=cmap, zorder=50, linewidth=line_width)
    lc.set_array(x)
    ax.add_collection(lc)

    return lc


def color_graph(ax, user, recolored_line=0, force_legend=False, match=False):
    colors = user["colors"]
    ax.set_facecolor(colors["graphbackground"])

    ax.figure.set_facecolor(colors["background"])

    for axis in ax.spines.values():
        axis.set_color(colors["axis"])

    ax.set_title(label=ax.get_title(), color=colors["text"])
    ax.xaxis.label.set_color(color=colors["text"])
    ax.yaxis.label.set_color(color=colors["text"])
    ax.tick_params(axis="both", which="both", colors=colors["axis"], labelcolor=colors["text"])

    ax.grid(color=colors["grid"])

    legend_lines = []
    legend_labels = []
    handler_map = {}
    line_color = colors["line"]

    for i, line in enumerate(ax.get_lines()):
        label = line.get_label()
        if label.startswith("_"):
            label = "\u200B" + label
        line_handler = LineHandler()
        if i == recolored_line:
            if line_color in plt.colormaps():
                line = cmap_line(ax, recolored_line, user)
                line_handler = CollectionHandler(numpoints=50)
            else:
                line.set_color(line_color)
                if int(user["id"]) == bot_owner:
                    line.set_linewidth(3)
        legend_lines.append(line)
        legend_labels.append(label)
        handler_map[line] = line_handler

    if len(legend_lines) > 1 or force_legend:
        if match:
            legend = ax.legend(legend_lines, legend_labels, handler_map=handler_map, loc="upper left",
                               bbox_to_anchor=(1.03, 1), borderaxespad=0, handletextpad=0.5)
            ax.set_position([0.1, 0.1, 0.6, 0.8])
        else:
            legend = ax.legend(legend_lines, legend_labels, handler_map=handler_map, loc="upper left", framealpha=0.5)

        legend.get_frame().set_facecolor(colors["graphbackground"])
        legend.get_frame().set_edgecolor(colors["axis"])
        for text in legend.get_texts():
            text.set_color(colors["text"])


def sample(user):
    x = [i for i in range(1000)]
    y = x

    ax = plt.subplots()[1]
    ax.plot(x, y, label="Data")

    plt.grid()
    ax.set_title("Sample Graph")
    ax.set_xlabel("X-Axis")
    ax.set_ylabel("Y-Axis")

    color_graph(ax, user, 0, True)

    plt.savefig("sample.png")

    plt.close()


def line(user, lines, title, x_label, y_label, file_name):
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

        if username == caller:
            caller_index = i
            if user["colors"]["line"] in plt.colormaps:
                x, y = get_interpolated_segments(x, y)

        ax.plot(x, y, label=username)

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


def compare(user, user1, user2, file_name):
    username1, data1 = user1
    username2, data2 = user2
    fig, (ax1, ax2) = plt.subplots(1, 2)

    color = user["colors"]["line"]
    if color in plt.colormaps():
        cmap = get_cmap(user)
        patches1 = ax1.hist(data1, bins="auto", orientation="horizontal")[2]
        patches2 = ax2.hist(data2, bins="auto", orientation="horizontal")[2]
        for i, patch in enumerate(patches1):
            patch.set_facecolor(cmap(i / len(patches1)))
        for i, patch in enumerate(patches2):
            patch.set_facecolor(cmap(i / len(patches2)))
    else:
        ax1.hist(data1, bins="auto", orientation="horizontal", color=color)
        ax2.hist(data2, bins="auto", orientation="horizontal", color=color)

    ax1.set_ylabel("WPM Difference")
    ax2.yaxis.tick_right()

    max_xlim = max(ax1.get_xlim()[1], ax2.get_xlim()[1])
    ax1.set_xlim(ax1.get_xlim()[::-1])
    ax2.set_xlim(0, max_xlim)

    min_ylim = min(ax1.get_ylim()[0], ax2.get_ylim()[0])
    max_ylim = max(ax1.get_ylim()[1], ax2.get_ylim()[1])
    ax1.set_ylim(min_ylim, max_ylim)
    ax2.set_ylim(min_ylim, max_ylim)

    ax1.grid()
    ax1.set_title(username1)

    ax2.grid()
    ax2.set_title(username2)

    color_graph(ax1, user)
    color_graph(ax2, user)

    plt.subplots_adjust(wspace=0, hspace=0)

    fig.suptitle(f"Text Bests Comparison", color=user["colors"]["text"])
    fig.text(0.5, 0.025, "Number of Texts", ha="center", color=user["colors"]["text"])

    plt.savefig(file_name)
    plt.close()


def improvement(user, wpm, title, file_name, timeframe=""):
    text_graph = "Text #" in title
    wpm = np.array(wpm)
    best_index, best = max(enumerate(wpm), key=lambda x: x[1])
    worst_index, worst = min(enumerate(wpm), key=lambda x: x[1])

    ax = plt.subplots()[1]

    max_window = 50 if text_graph else 500
    window_size = min(max(len(wpm) // 15, 1), max_window)
    moving_wpm = np.convolve(wpm, np.ones(window_size) / window_size, mode="valid")

    downsample_factor = max(len(wpm) // 100000, 1)
    downsampled_indices = np.arange(0, len(wpm), downsample_factor)
    downsampled_data = wpm[downsampled_indices]
    downsampled_indices = [d + 1 for d in downsampled_indices]

    race_count = np.arange(window_size - 1, len(wpm))
    race_count = [r + 1 for r in race_count]

    bg_color = hex2color(user["colors"]["graphbackground"])
    point_color = "white" if np.mean(bg_color) < 0.5 else "black"

    ax.scatter(worst_index + 1, worst, color="#FA3244", marker=".", zorder=10)
    ax.scatter(best_index + 1, best, color="#53D76A", marker=".", zorder=10)
    ax.scatter(downsampled_indices, downsampled_data, alpha=0.1, s=25, color=point_color, edgecolors="none")

    # Interpolating for smooth colormaps
    segment_count = 50 // (len(moving_wpm) - 1) if len(moving_wpm) > 1 else 1
    if segment_count > 1:
        x_segments = []
        y_segments = []
        for i in range(len(moving_wpm) - 1):
            value = moving_wpm[i]
            segments = np.linspace(value, moving_wpm[i + 1], segment_count)
            for v in segments[:-1]:
                y_segments.append(v)

            segments = np.linspace(i + 1, i + 2, segment_count)
            for v in segments[:-1]:
                x_segments.append(v)

        y_segments.append(moving_wpm[-1])
        x_segments.append(race_count[-1])

        ax.plot(x_segments, y_segments)

    else:
        ax.plot(race_count, moving_wpm)

    ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))
    # if not text_graph:
    #     ax.set_ylim(0, plt.ylim()[1])

    ax.set_xlabel(f"Races{timeframe}")
    ax.set_ylabel("WPM")
    if window_size > 1:
        title += f"\nMoving Average of {window_size} Races"
    ax.set_title(title)
    ax.grid()

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()


def match(user, rankings, title, y_label, file_name, limit_y=True):
    ax = plt.subplots()[1]
    caller_index = 0
    starts = []
    remaining = []

    if "average_adjusted_wpm" in rankings[0]:
        racer = rankings[0]
        instant_chars = racer["instant_chars"]
        average_wpm = racer["average_adjusted_wpm"][instant_chars:]
        keystrokes = np.arange(instant_chars + 1, len(average_wpm) + instant_chars + 1)
        ax.plot(keystrokes, average_wpm)
        starts += average_wpm[:9]
        remaining += average_wpm[9:]

    else:
        caller = user["username"]
        for i, racer in enumerate(rankings):
            zorder = len(rankings) + 5 - i
            print(zorder)
            racer_username = racer["username"]
            if racer_username == caller:
                caller_index = i
                zorder *= 10
            average_wpm = racer["average_wpm"]
            keystrokes = np.arange(1, len(average_wpm) + 1)
            ax.plot(keystrokes, average_wpm, label=racer_username, zorder=zorder)
            starts += average_wpm[:9]
            remaining += average_wpm[9:]

        ax.set_ylim(0, plt.ylim()[1])

    if remaining and limit_y:
        if max(starts) > max(remaining):
            ax.set_ylim(0, 1.2 * max(remaining))

    ax.set_xlabel("Keystrokes")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid()

    color_graph(ax, user, caller_index, match=True)

    plt.savefig(file_name)
    plt.close()


def histogram(user, username, values, category, file_name):
    category_title = "WPM"
    y_label = "WPM"
    bins = "auto"
    if category == "accuracy":
        values = [value for value in values if value >= 90]
        bins = np.arange(min(values), 102, 1)
        category_title = "Accuracy"
        y_label = "Accuracy %"

    ax = plt.subplots()[1]

    color = user["colors"]["line"]
    if color in plt.colormaps():
        cmap = get_cmap(user)
        patches = ax.hist(values, bins=bins)[2]
        for i, patch in enumerate(patches):
            patch.set_facecolor(cmap(i / len(patches)))
    else:
        ax.hist(values, bins=bins, color=color)

    if category == "accuracy":
        x_ticks = ax.get_xticks()
        ax.set_xticks(x_ticks + 0.5, [int(value) for value in x_ticks])
        ax.set_xlim(max(ax.set_xlim()[0], 90), 101)

    ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))
    ax.set_xlabel(y_label)
    ax.set_ylabel("Frequency")
    ax.set_title(f"{category_title} Histogram - {username}")
    ax.grid()

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()


def histogram_time(user, username, activity, file_name): # Maybe for the future, another command
    ax = plt.subplots()[1]
    timestamps = [day[0] for day in activity]
    timestamps = [i for i in range(len(activity))]
    seconds = [int(day[1]) for day in activity]

    print(timestamps[-1])
    print(seconds[-1])
    print(timestamps[-2])
    print(seconds[-2])

    # color = user["colors"]["line"]
    # if color in plt.colormaps():
    #     cmap = plt.get_cmap(color)
    #     patches = ax.hist2d(timestamps, seconds, bins="auto")[3]
    #     for i, patch in enumerate(patches):
    #         patch.set_facecolor(cmap(i / len(patches)))
    # else:
    ax.bar(timestamps, seconds)

    # ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))
    # ax.set_xlim(left=1709269200)
    ax.set_xlabel("Date")
    ax.set_ylabel("Race Time")

    # ax.set_xticks([utils.format_duration_short(seconds) for seconds in ax.get_xticks()])

    ax.set_title(f"Daily Activity Histogram - {username}")
    ax.grid()

    # color_graph(ax, user["colors"])

    plt.savefig(file_name)
    plt.close()


def personal_bests(user, username, x, y, category, file_name):
    ax = plt.subplots()[1]

    x_segments, y_segments = get_interpolated_segments(x, y)
    ax.plot(x_segments, y_segments)

    bg_color = hex2color(user["colors"]["graphbackground"])
    point_color = "white" if np.mean(bg_color) < 0.5 else "black"
    ax.scatter(x, y, alpha=0.5, s=25, color=point_color, edgecolors="none")

    if category == "races":
        ax.set_xlabel("Races")
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))
    else:
        ax.set_xlabel("Date")
        date_x_ticks(ax, x[0], x[-1])

    ax.set_ylabel("WPM")
    plt.grid()
    ax.set_title(f"Personal Best Over {category.title()} - {username}")

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()

def text_bests(user, username, x, y, category, file_name):
    ax = plt.subplots()[1]
    x_segments, y_segments = get_interpolated_segments(x, y)
    ax.plot(x_segments, y_segments)

    if category == "races":
        title = "Races"
        ax.set_xlabel("Races")
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))
    elif category == "time":
        title = "Time"
        ax.set_xlabel("Date")
        date_x_ticks(ax, x[0], x[-1])
    else:
        title = "Text Changes"
        ax.set_xlabel("Text Changes")
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))

    ax.set_ylabel("WPM")
    plt.grid()
    ax.set_title(f"Text Bests Over {title} - {username}")

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()