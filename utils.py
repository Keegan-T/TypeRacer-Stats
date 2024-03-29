import re
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import matplotlib.colors as mcolors
import urls
import time
from database.bot_users import get_user


def get_display_number(number):
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    if number % 100 in [11, 12, 13]:
        suffix = "th"

    return f"{number:,}{suffix}"


def get_display_date(date):
    month = date.strftime("%B")
    year = date.strftime("%Y")
    day = int(date.strftime("%d"))

    return f"{month} {get_display_number(day)}, {year}"


def get_display_date_range(start, end):
    start_year, end_year = start.year, end.year
    start_month, end_month = start.strftime("%B"), end.strftime("%B")
    start_day, end_day = get_display_number(start.day), get_display_number(end.day),

    if start_year == end_year and start_month == end_month and start_day == end_day:
        return get_display_date(start)

    display_string = (f"{start_month} {start_day}, {start_year} - "
                      f"{end_month} {end_day}, {end_year}")

    if start_year == end_year:
        display_string = display_string.replace(f", {start_year}", "", 1)

        if start_month == end_month:
            temp_month = f"{start_month} "[::-1]
            temp_string = display_string[::-1]
            temp_string = temp_string.replace(temp_month, "", 1)
            display_string = temp_string[::-1]

    return display_string


def split_log(log):
    escapes = ''.join([chr(char) for char in range(1, 32)])
    log = log.encode().decode('unicode-escape').translate(escapes)
    log = log

    quote = ""
    delays = []

    current_num = ""
    i = 0
    while i < len(log):
        char = log[i]
        if char.isdigit():
            current_num += char
        else:
            if char == "\t":
                i += 1
                quote += log[i]
            else:
                quote += char
            if current_num:
                delays.append(int(current_num))
            current_num = ""
        i += 1

    delays.append(int(current_num))

    return quote, delays


def get_log_details(log):
    quote, delays = split_log(log)

    total_ms = sum(delays)
    unlagged = len(quote) / ((total_ms / 1000) / 12)
    adjusted = (len(quote) - 1) / (((total_ms - delays[0]) / 1000) / 12)
    start = delays[0]

    details = {
        "quote": quote,
        "delays": delays,
        "ms": total_ms,
        "unlagged": unlagged,
        "adjusted": adjusted,
        "start": start,
    }

    return details


def get_raw_speeds(typing_log):
    escapes = ''.join([chr(char) for char in range(1, 32)])
    typing_log = typing_log.encode().decode('unicode-escape').translate(escapes).split('|', 1)
    times = [int(c) for c in re.findall(r"\d+", typing_log[0])][2:]

    actions = []
    for keystroke in re.findall("\d+,(?:\d+[\+\-$].?)+,", typing_log[1]):
        chars = re.findall('(?:\d+[\+\-$].?)', keystroke)
        if chars[0][-2] == '$': chars = chars[1:] + ['0-k', chars[0]]

        for i, char in enumerate(chars):
            if i > 0:
                actions.append([char[-2], 0])
            else:
                actions.append([char[-2], int(keystroke.split(',')[0])])

    raw_times = []
    for action in actions:
        if action[0] == '+' or action[0] == '$':
            raw_times.append(action[1])
        else:
            raw_times.pop()

    return {
        "raw_start": raw_times[0],
        "duration": sum(times),
        "raw_duration": sum(raw_times),
        "correction": sum(times) - sum(raw_times),
        "adjusted_correction": sum(times[1:]) - sum(raw_times[1:]),
        "delays": raw_times,
    }


def calculate_points(quote, wpm):
    return (wpm / 60) * len(quote.split(" "))


def calculate_seconds(quote, wpm):
    if wpm == 0: return 0
    return (len(quote) * 12) / wpm


def get_text_stats(text_bests):
    text_wpm_total = 0
    for text_best in text_bests:
        text_wpm_total += text_best["wpm"]

    texts_typed = len(text_bests)
    text_best_average = text_wpm_total / texts_typed

    text_stats = {
        'texts_typed': texts_typed,
        'text_best_average': text_best_average,
        'text_wpm_total': text_wpm_total,
    }

    return text_stats


# Formats seconds into: XXd XXh XXm XXs
def format_duration_short(seconds, round_seconds=True):
    if round_seconds:
        seconds = round(seconds)
    if seconds == 0: return "0s"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    days = f"{d:,.0f}d " * (d != 0)
    hours = f"{h:,.0f}h " * (h != 0)
    minutes = f"{m:,.0f}m " * (m != 0)
    seconds = f"{round(s, 0 if round_seconds else 2)}s " * (s != 0)

    return f"{days}{hours}{minutes}{seconds}"[:-1]


# Formats seconds int: XX days, XX hours, XX minutes, XX seconds
def format_duration(seconds):
    seconds = round(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    days = f"{d:,} day{'s' * (d > 1)}, " * (d != 0)
    hours = f"{h} hour{'s' * (h > 1)}, " * (h != 0)
    minutes = f"{m} minute{'s' * (m > 1)}, " * (m != 0)
    seconds = f"{s} second{'s' * (s > 1)}, " * (s != 0)
    return f"{days}{hours}{minutes}{seconds}"[:-2]


def format_big_number(number, _):
    if number >= 1_000_000:
        return f"{round(number / 1_000_000, 1)}M".replace(".0", "")
    elif number >= 1_000:
        return f"{round(number / 1_000, 1)}K".replace(".0", "")

    return int(number)


def parse_duration_string(duration):
    try:
        duration = float(duration)
        return duration
    except ValueError:
        pass

    units = {"d": 0, "h": 0, "m": 0, "s": 0}

    durations = re.findall(r'(\d+(?:\.\d+)?)(\D*)', duration)

    for value, unit in durations:
        value = float(value)
        unit = unit.strip()
        if unit not in units:
            raise ValueError
        if units[unit] > 0:
            raise ValueError
        else:
            units[unit] = value

    return units["d"] * 86400 + units["h"] * 3600 + units["m"] * 60 + units["s"]


def parse_value_string(value):
    try:
        value = int(value)
        return value
    except ValueError:
        try:
            value = float(value)
            return value
        except ValueError:
            value = value.replace(",", "")
            try:
                value = int(value)
                return value
            except ValueError:
                pass

    value = value.lower()
    if value[-1] == "k":
        return round(float(value[:-1]) * 1_000)
    elif value[-1] == "m":
        return round(float(value[:-1]) * 1_000_000)
    else:
        raise ValueError


def count_unique_dates(start, end):
    start_date = datetime.fromtimestamp(start, tz=timezone.utc)
    end_date = datetime.fromtimestamp(end, tz=timezone.utc)

    unique_dates = set()

    while start_date <= end_date:
        unique_dates.add(start_date.strftime("%m-%d-%Y"))
        start_date += relativedelta(days=1)

    return len(unique_dates)


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


def add_profile(embed, stats, pfp=True):
    username = stats["username"]
    author_icon = (
        f"https://flagsapi.com/{stats['country'].upper()}/flat/64.png"
        if stats["country"]
        else "https://i.imgur.com/TgHElrb.png"
    )

    if pfp:
        embed.set_thumbnail(url=urls.profile_picture(username))

    embed.set_author(
        name=username,
        url=urls.profile(username),
        icon_url=author_icon,
    )

    return embed


def add_universe(embed, universe):
    if universe != "play":
        embed.set_footer(text=f"Universe: {universe}")


def truncate_clean(text, max_chars):
    if len(text) <= max_chars:
        return escape_discord_format(text)

    substring = text[:max_chars]
    while True:
        if substring[-2].isalnum() and not substring[-1].isalnum():
            break
        substring = substring[:-1]
    substring = substring[:-1]
    substring += "..."

    return escape_discord_format(substring)


def escape_discord_format(string):
    return (string
            .replace("*", "\\*")
            .replace("_", "\\_")
            .replace("~", "\\~")
            .replace("`", ""))


def text_description(text):
    if "text_id" not in text:
        text["text_id"] = text["id"]
    quote = text["quote"]
    words = len(quote.split(" "))
    chars = len(quote)
    quote = truncate_clean(quote, 1000)

    return (f"**Text** - [#{text['text_id']}]"
            f"({urls.trdata_text(text['text_id'])}) - "
            f"{words:,} words - {chars:,} characters\n"
            f'"{quote}"')


def get_wpm_over_keystrokes(delays):
    if delays[0] == 0:  # I still think this is wrong butttt I don't know if I care
        return get_adjusted_wpm_over_keystrokes(delays)[0]

    average_wpm = []

    total_ms = 0
    for i, delay in enumerate(delays):
        chars = i + 1
        total_ms += delay
        wpm = chars / ((total_ms / 1000) / 12)
        average_wpm.append(wpm)

    return average_wpm


def get_adjusted_wpm_over_keystrokes(delays):
    average_wpm = []

    instant_chars = 1
    for delay in delays[1:]:
        if delay == 0:
            instant_chars += 1
        else:
            break

    total_ms = 0
    i = 0
    while i < len(delays):
        delay = delays[i]
        chars = i + 1
        if chars == 1:
            average_wpm += [float("inf")] * instant_chars
            i += instant_chars
        else:
            total_ms += delay
            wpm = (chars - 1) / ((total_ms / 1000) / 12)
            average_wpm.append(wpm)
            i += 1

    return average_wpm, instant_chars


start = 0


def time_start():
    global start
    start = time.time()


def time_split():
    time_end()
    time_start()


def time_end():
    end = time.time() - start
    print(f"Took {end:,.2f}s")


def get_competition_type_string(kind):
    if kind == "day":
        return "Daily"
    else:
        return kind.title() + "ly"


category_aliases = [
    ["races", "r"],
    ["points", "pts", "p"],
    ["wpm", "speed"],
    ["day", "d"],
    ["week", "w"],
    ["month", "m"],
    ["year", "y"],
    ["awards", "medals", "aw", "md"],
    ["textbests", "tb"],
    ["textstyped", "tt"],
    ["toptens", "top10s", "10s"],
    ["textrepeats", "tr", "cog"],
    ["totaltextwpm", "tw"],
    ["racetime", "rt", "seconds", "s"],
    ["characters", "chars", "c"],
    ["time", "t"],
    ["texts"],
    ["times"],
    ["accuracy", "acc", "ac"],
    ["embed", "em"],
    ["background", "bg"],
    ["graphbackground", "graphbg", "gbg", "gb"],
    ["axis", "ax"],
    ["line", '-'],
    ["text", "txt"],
    ["grid", "#"],
]


def get_category(options, param):
    param = param.lower()
    categories = {}

    for aliases in category_aliases:
        for category in aliases:
            categories[category] = aliases

    if param in categories:
        category = categories[param][0]
        if category in options:
            return category

    return None


def get_type_title(kind):
    titles = {
        "races": "Races",
        "points": "Points",
        "wpm": "WPM",
    }

    if kind in titles:
        return titles[kind]

    return None


def reset_cooldown(function, ctx):
    function.reset_cooldown(ctx)


def get_discord_id(string):
    if "&" in string:
        return None

    if (string.startswith("<@") and string.endswith(">")) or (string.isnumeric() and 17 <= len(string) <= 19):
        id = string.translate(string.maketrans("", "", "<@>"))
        return id

    return None


def floor_day(date):
    return date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def floor_week(date):
    return ((date - relativedelta(days=date.weekday()))
            .replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc))


def floor_month(date):
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def floor_year(date):
    return date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def now():
    return datetime.now(timezone.utc)


def discord_timestamp(timestamp, style="R"):
    return f"<t:{int(timestamp)}:{style}>"


def get_sort_title(sort):
    if sort == "wpm": return "WPM"
    return sort.title()


def rank(number):
    emojis = [
        ":first_place:",
        ":second_place:",
        ":third_place:",
        "<:4_trs:1219161348253159444>",
        "<:5_trs:1219161347082944563>",
        "<:6_trs:1219163724531892224>",
        "<:7_trs:1219163723650826260>",
        "<:8_trs:1219163721704931370>",
        "<:9_trs:1219163722455453707>",
        "<:10_trs:1219163725223694336>",
    ]

    if 1 <= number <= 10:
        return emojis[number - 1]

    return str(number)


def command_log(ctx):
    user = get_user(ctx.author.id)
    linked = user["username"]
    author = ctx.author
    server = ctx.guild.name if ctx.guild else "DM"
    if hasattr(ctx, "message"):
        message = ctx.message.content
    else:
        message = ctx.content

    return (
        f"`{server} | [{author.id}] {author.name} "
        f"{('(' + linked + ')') if linked else ''}: {message}`"
    )

def race_id(username, number):
    return f"{username}|{number}"