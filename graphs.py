from datetime import datetime, timezone
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, hex2color
from matplotlib.legend_handler import HandlerLineCollection
from matplotlib.legend_handler import HandlerLine2D
from matplotlib.ticker import FuncFormatter
from matplotlib import rcParams, patches
import numpy as np
from utils import format_big_number
from config import bot_owner

default_palette = [
    "#00E1FF", "#E41A1C", "#4DAF4A", "#FF7F00", "#7C3AFF",
    "#FFFF33", "#00C299", "#F781BF", "#999999", "#A65628",
]
rcParams["axes.prop_cycle"] = plt.cycler(color=default_palette)
rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["Exo 2"]
rcParams["font.size"] = 11
cmap_keegant = LinearSegmentedColormap.from_list("keegant", ["#0094FF", "#FF00DC"])
plt.register_cmap(name="keegant", cmap=cmap_keegant)

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


def date_x_ticks(ax, min_timestamp, max_timestamp):
    date_range = max_timestamp - min_timestamp
    step = date_range / 5

    ticks = [min_timestamp + step * i for i in range(6)]
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
    cmap = plt.get_cmap(user["colors"]["line"])
    if cmap.name == "keegant":
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


def cmap_histogram(ax, user, counts, groups):
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

def cmap_compare(ax, user, counts, groups, extent):
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


def cmap_bar(ax, user, labels, wpm, raw_wpm):
    cmap = plt.get_cmap(user["colors"]["line"])

    bars = ax.bar(labels, wpm, alpha=0)
    original_ylim = ax.get_ylim()

    extent = [ax.get_xlim()[0], ax.get_xlim()[1], 0, max(wpm)]

    x = np.linspace(0, 10, 100)
    y = np.linspace(0, 10, 100)
    X, Y = np.meshgrid(x, y)

    ax.imshow(Y, cmap=cmap, extent=extent, origin="lower", aspect="auto")
    ax.set_ylim(original_ylim)

    graph_background = user["colors"]["graphbackground"]
    bar_width = bars[0].get_width()

    max_y = 0
    for i, bar in enumerate(bars):
        target_y_value = raw_wpm[i]
        bar_height = bar.get_height()
        bar_left = bar.get_x()
        if bar_height < target_y_value:
            if target_y_value > max_y:
                max_y = target_y_value
            rect = patches.Rectangle((bar_left, bar_height), bar_width,
                                     target_y_value - bar_height, color=user["colors"]["raw"])
            ax.add_patch(rect)

    if original_ylim[1] < max_y:
        ax.set_ylim(top=max_y * 1.05)
        original_ylim = (0.0, max_y * 1.05)

    for i in range(len(labels) - 1):
        left = labels[i] + bar_width / 2
        right = labels[i + 1] - bar_width / 2
        rect = patches.Rectangle((left, 0), right - left, original_ylim[1], color=graph_background)
        ax.add_patch(rect)

    bars = ax.bar(labels, raw_wpm, alpha=0)
    for bar in bars:
        bar_height = bar.get_height()
        bar_left = bar.get_x()
        rect = patches.Rectangle((bar_left, bar_height), bar_width,
                                 original_ylim[1] - bar_height, color=graph_background)
        ax.add_patch(rect)

    left_padding = ax.get_xlim()[0]
    right_padding = ax.get_xlim()[1]

    rect_left = patches.Rectangle((left_padding, 0), labels[0] - bar_width / 2 - left_padding,
                                  original_ylim[1], color=graph_background)
    ax.add_patch(rect_left)

    rect_right = patches.Rectangle((labels[-1] + bar_width / 2, 0), right_padding - (labels[-1] + bar_width / 2),
                                   original_ylim[1], color=graph_background)
    ax.add_patch(rect_right)


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

    if colors["grid"] == "off":
        ax.grid(False)
    else:
        ax.grid(color=colors["grid"])

    legend_lines = []
    legend_labels = []
    handler_map = {}
    line_color = colors["line"]

    for i, line in enumerate(ax.get_lines()):
        label = line.get_label()
        if label == "Raw Adjusted":
            line.set_color(user["colors"]["raw"])
            if int(user["id"]) != bot_owner:
                line.set_linewidth(1)
            recolored_line = 1
        if label.startswith("_"):
            label = "\u200B" + label
        line_handler = LineHandler()
        if i == recolored_line:
            if line_color in plt.colormaps():
                line = cmap_line(ax, recolored_line, user)
                line_handler = CollectionHandler(numpoints=50)
            else:
                line.set_color(line_color)
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
    x = [i for i in range(100)]
    y = x

    x2 = [i for i in range(50)]
    y2 = [i + 50 for i in x2]

    ax = plt.subplots()[1]
    ax.plot(x, y, label="Data")
    ax.plot(x2, y2, label="Raw Speed", color=user["colors"]["raw"], zorder=10)

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

        x, y = get_interpolated_segments(x, y)
        ax.plot(x, y, label=username)

        if username == caller:
            caller_index = i

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
        cmap_compare(ax1, user, counts1, groups1, [0, max(counts1), min_ylim, max_ylim])
        cmap_compare(ax2, user, counts2, groups2, [0, max(counts2), min_ylim, max_ylim])

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


def improvement(user, wpm, title, file_name, timeframe="", timestamps=None, universe="play"):
    text_graph = "Text #" in title
    wpm = np.array(wpm)
    best_index, best = max(enumerate(wpm), key=lambda x: x[1])
    worst_index, worst = min(enumerate(wpm), key=lambda x: x[1])

    ax = plt.subplots()[1]

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
        x_segments, y_segments = get_interpolated_segments(x_points, moving_wpm)
        ax.plot(x_segments, y_segments)
        # x_segments = []
        # y_segments = []
        # for i in range(len(moving_wpm) - 1):
        #     value = moving_wpm[i]
        #     segments = np.linspace(value, moving_wpm[i + 1], segment_count)
        #     for v in segments[:-1]:
        #         y_segments.append(v)
        #
        #     segments = np.linspace(x_points[i], x_points[i + 1], segment_count)
        #     for v in segments[:-1]:
        #         x_segments.append(v)
        #
        # y_segments.append(moving_wpm[-1])
        # x_segments.append(x_points[-1])
    else:
        ax.plot(x_points, moving_wpm)

    ax.set_xlabel(f"Races{timeframe}")
    ax.set_ylabel("WPM")
    if window_size > 1:
        title += f"\nMoving Average of {window_size} Races"
    if universe != "play":
        separator = " | " if "\n" in title else "\n"
        title += f"{separator}Universe: {universe}"
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
    comparison = False

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
            racer_username = racer["username"]
            if racer_username in [caller, "Adjusted"]:
                caller_index = i
                zorder *= 10
                if racer_username == "Adjusted":
                    comparison = True
            average_wpm = racer["average_wpm"]
            keystrokes = np.arange(1, len(average_wpm) + 1)
            ax.plot(keystrokes, average_wpm, label=racer_username, zorder=zorder)
            starts += average_wpm[:9]
            remaining += average_wpm[9:]

        if not comparison:
            ax.set_ylim(bottom=0)

    if remaining and limit_y:
        if max(starts) > max(remaining):
            ax.set_ylim(top=1.2 * max(remaining))

    ax.set_xlabel("Keystrokes")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid()

    color_graph(ax, user, caller_index, match=True)

    plt.savefig(file_name)
    plt.close()


def histogram(user, username, values, category, file_name, universe):
    category_title = "WPM"
    y_label = "WPM"
    bins = "auto"

    if category == "accuracy":
        values = np.array(values)
        values = values[values >= 90]
        bins = np.arange(min(values), 102, 1)
        category_title = "Accuracy"
        y_label = "Accuracy %"

    elif category == "textbests":
        category_title = "Text Bests"

    ax = plt.subplots()[1]
    counts, groups = np.histogram(values, bins=bins)

    color = user["colors"]["line"]

    if color in plt.colormaps():
        cmap_histogram(ax, user, counts, groups)

    # if color in plt.colormaps():
    #     cmap = plt.get_cmap(user["colors"]["line"])
    #     counts, groups = np.histogram(values, bins=bins)
    #     patches = ax.bar(groups[:-1], counts, width=np.diff(groups), align="edge")
    #     for i, patch in enumerate(patches):
    #         patch.set_facecolor(cmap(i / len(patches)))
    else:
        ax.bar(groups[:-1], counts, width=np.diff(groups), align="edge", color=color)

    if category == "accuracy":
        x_ticks = ax.get_xticks()
        ax.set_xticks(x_ticks + 0.5, [int(value) for value in x_ticks])
        ax.set_xlim(max(ax.get_xlim()[0], 90), 101)

    ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))
    ax.set_xlabel(y_label)
    ax.set_ylabel("Frequency")
    title = f"{category_title} Histogram - {username}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    ax.set_title(title)
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


def personal_bests(user, username, x, y, category, file_name, universe):
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
    title = f"Personal Best Over {category.title()} - {username}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    ax.set_title(title)

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()

def text_bests(user, username, x, y, category, file_name, universe):
    ax = plt.subplots()[1]
    x_segments, y_segments = get_interpolated_segments(x, y)
    ax.plot(x_segments, y_segments)

    if category == "races":
        ax.set_xlabel("Races")
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))
    elif category == "time":
        ax.set_xlabel("Date")
        date_x_ticks(ax, x[0], x[-1])
    else:
        category = "text changes"
        ax.set_xlabel("Text Changes")
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))

    ax.set_ylabel("WPM")
    plt.grid()
    title = f"Text Bests Over {category.title()} - {username}"
    if universe != "play":
        title += f"\nUniverse: {universe}"
    ax.set_title(title)

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()

def race_wpm(user, segments, title, file_name):
    ax = plt.subplots()[1]
    x = [i + 1 for i in range(len(segments))]
    y = [segment["wpm"] for segment in segments]
    raw_y = [segment["raw_wpm"] for segment in segments]

    color = user["colors"]["line"]
    if color in plt.colormaps():
        cmap_bar(ax, user, x, y, raw_y)
    else:
        ax.bar(x, y, color=color)
        ax.bar(x, raw_y, color=user["colors"]["raw"], zorder=0)

    ax.set_ylabel("WPM")
    ax.set_xlabel("Segments")
    plt.grid()
    ax.set_title(title)

    color_graph(ax, user)

    plt.savefig(file_name)
    plt.close()