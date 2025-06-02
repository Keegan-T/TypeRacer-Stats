import numpy as np
from matplotlib import pyplot as plt

from graphs.core import color_graph, universe_title, file_name


def render(user, username, activity, universe, offset=0):
    color = user["colors"]["line"]
    fig = plt.figure()
    ax = fig.add_subplot(111, polar=True)

    num_bars = len(activity)
    theta = np.linspace(0, 2 * np.pi, num_bars, endpoint=False)
    bar_width = 2 * np.pi / num_bars
    theta += bar_width / 2
    theta += np.deg2rad(offset * 360 / num_bars)

    if color in plt.colormaps():
        apply_cmap(ax, user, activity, offset)
    else:
        ax.bar(theta, activity, width=bar_width, bottom=0, color=color)

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    ax.set_xticks(np.linspace(0, 2 * np.pi, 24, endpoint=False))
    ax.set_xticklabels([f"{h}" for h in range(24)])
    ax.set_yticklabels([])
    ax.set_yticks([])

    offset_string = "(UTC)"
    if offset < 0:
        offset_string = f"(UTC{offset})"
    elif offset > 0:
        offset_string = f"(UTC+{offset})"
    title = f"Daily Activity {offset_string} - {username}"

    ax.set_title(universe_title(title, universe))
    plt.tight_layout()

    color_graph(ax, user)

    file = file_name(f"activity_{username}")
    plt.savefig(file)
    plt.close(fig)

    return file


def apply_cmap(ax, user, activity, offset):
    cmap = plt.get_cmap(user["colors"]["line"])

    offset = offset % 24
    activity = activity[-offset:] + activity[:-offset]

    num_bars = len(activity)
    bar_width = 2 * np.pi / num_bars
    samples_per_bar = 50
    num_samples = num_bars * samples_per_bar
    theta_edges = np.linspace(0, 2 * np.pi, num_samples + 1)
    expanded_activity = np.repeat(activity, samples_per_bar)
    max_activity = max(activity) * 1.05

    r_grid = np.linspace(0, 1, 300)
    Theta, R = np.meshgrid(theta_edges, r_grid)
    mask = np.ones_like(Theta)

    for i in range(num_samples):
        angle_min = theta_edges[i]
        angle_max = theta_edges[i + 1]
        radial_extent = expanded_activity[i] / max_activity
        angle_mask = (Theta >= angle_min) & (Theta <= angle_max)
        radial_mask = R <= radial_extent
        mask[angle_mask & radial_mask] = 0

    masked_values = np.ma.masked_array(R, mask)
    ax.pcolormesh(Theta, R, masked_values, cmap=cmap, shading="auto")

    bar_centers = np.linspace(0, 2 * np.pi, num_bars, endpoint=False) + bar_width / 2
    for angle, val in zip(bar_centers, activity):
        ax.bar(
            angle, val / max_activity, width=bar_width, bottom=0,
            edgecolor=user["colors"]["graphbackground"], facecolor="none", linewidth=0.1
        )
