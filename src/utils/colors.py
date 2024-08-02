import matplotlib.colors as mcolors

error = 0xFF0000
gold = 0xFFB600
warning = 0xFFC107
success = 754944

default_colors = {
    "embed": 0x1F51FF,
    "background": "#ffffff",
    "graphbackground": "#ffffff",
    "axis": "#000000",
    "line": "#157EFD",
    "text": "#000000",
    "grid": "#b0b0b0",
    "raw": "#ffb600",
}

graph_palette = [
    "#00E1FF", "#E41A1C", "#4DAF4A", "#FF7F00", "#7C3AFF",
    "#FFFF33", "#00C299", "#F781BF", "#999999", "#A65628",
]


def parse_color(color):
    if type(color) == int:
        return color
    try:
        number = int(color, 16)
    except ValueError:
        try:
            hex_code = mcolors.to_hex(color)
            number = int(hex_code[1:], 16)
        except ValueError:
            return None

    if number < 0 or number > 0xFFFFFF:
        return None
    return number
