import numpy as np
from matplotlib import pyplot as plt

from graphs.core import color_graph, universe_title, file_name


def render(user, username, activity, universe):
    color = user["colors"]["line"]
    fig = plt.figure()
    ax = fig.add_subplot(111, polar=True)

    if color in plt.colormaps():
        apply_cmap(ax, user, activity)
    else:
        num_bars = len(activity)
        theta = np.linspace(0, 2 * np.pi, num_bars, endpoint=False)
        bar_width = 2 * np.pi / num_bars
        theta += bar_width / 2
        ax.bar(theta, activity, width=2 * np.pi / num_bars, bottom=0, color=color)

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    ax.set_xticks(np.linspace(0, 2 * np.pi, 24, endpoint=False))
    ax.set_xticklabels([f"{h}" for h in range(24)])
    ax.set_yticklabels([])
    ax.set_yticks([])
    title = f"Daily Activity (UTC) - {username}"
    ax.set_title(universe_title(title, universe))
    plt.tight_layout()

    color_graph(ax, user)

    file = file_name(f"activity_{username}")
    plt.savefig(file)
    plt.close(fig)

    return file


def apply_cmap(ax, user, activity):
    cmap = plt.get_cmap(user["colors"]["line"])

    num_bars = len(activity)
    theta_locations = np.linspace(0, 2 * np.pi, num_bars, endpoint=False)
    bar_width = 2 * np.pi / 24
    for i in range(len(theta_locations)):
        theta_locations[i] += bar_width / 2
    max_activity = max(activity) * 1.05

    theta_grid = np.linspace(0, 2 * np.pi, 1000)
    r_grid = np.linspace(0, 1, 100)
    Theta, R = np.meshgrid(theta_grid, r_grid)
    values = R
    mask = np.ones_like(values)

    bar_width = (2 * np.pi / num_bars)
    for angle, val in zip(theta_locations, activity):
        angle_min = angle - bar_width / 2
        angle_max = angle + bar_width / 2

        if angle_min < 0:
            angle_mask = (Theta >= angle_min + 2 * np.pi) | (Theta <= angle_max)
        elif angle_max > 2 * np.pi:
            angle_mask = (Theta >= angle_min) | (Theta <= angle_max - 2 * np.pi)
        else:
            angle_mask = (Theta >= angle_min) & (Theta <= angle_max)

        radial_extent = val / max_activity
        radial_mask = (R <= radial_extent)

        mask[angle_mask & radial_mask] = 0

    masked_values = np.ma.masked_array(values, mask)
    ax.pcolormesh(Theta, R, masked_values, cmap=cmap, shading="auto")

    for angle, val in zip(theta_locations, activity):
        ax.bar(
            angle, val / max_activity, width=bar_width, bottom=0,
            edgecolor=user["colors"]["graphbackground"], facecolor="none", linewidth=0.1
        )
