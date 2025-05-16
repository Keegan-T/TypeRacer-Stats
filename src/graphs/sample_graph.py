from graphs.core import plt, color_graph, file_name


def render(user):
    x = [i for i in range(100)]
    y = x

    x2 = [i for i in range(50)]
    y2 = [i + 50 for i in x2]

    fig, ax = plt.subplots()
    ax.plot(x, y, label="Data")
    ax.plot(x2, y2, label="Raw Speed", color=user["colors"]["raw"], zorder=10)

    plt.grid()
    ax.set_title("Sample Graph")
    ax.set_xlabel("X-Axis")
    ax.set_ylabel("Y-Axis")

    color_graph(ax, user, 0, True)

    plt.savefig(file_name("sample"))
    plt.close(fig)
