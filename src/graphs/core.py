import os
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.legend_handler import HandlerLine2D
from matplotlib.legend_handler import HandlerLineCollection

from config import bot_owner
from utils.colors import graph_palette

rcParams["axes.prop_cycle"] = plt.cycler(color=graph_palette)
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


def interpolate_segments(x, y):
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


def get_line_cmap(ax, line_index, user):
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
                line = get_line_cmap(ax, recolored_line, user)
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


def remove_file(file_name):
    try:
        os.remove(file_name)
    except (FileNotFoundError, PermissionError):
        return
    except Exception:
        raise Exception
