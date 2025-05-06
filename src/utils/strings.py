import re
from datetime import datetime, timezone

import commands.recent as recent
from utils import errors, urls, dates

category_aliases = [
    ["races", "r"],
    ["points", "pts", "p"],
    ["wpm", "speed"],
    ["day", "d"],
    ["miniday", "md"],
    ["yesterday", "yd"],
    ["miniyesterday", "myd"],
    ["week", "w"],
    ["lastweek", "yesterweek", "lw", "yw"],
    ["miniweek", "mw"],
    ["month", "m"],
    ["lastmonth", "yestermonth", "lm", "ym"],
    ["minimonth", "mm"],
    ["year", "y"],
    ["lastyear", "yesteryear", "ly", "yy"],
    ["miniyear", "my"],
    ["awards", "medals", "aw"],
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
    ["raw", "rawspeed"],
    ["text", "txt"],
    ["grid", "#"],
    ["best"],
    ["worst"],
    ["random", "rand", "r"],
    ["old", "oldest"],
    ["new", "newest"],
    ["textperformances", "tp"],
    ["all", "alltime"]
]
rank_emojis = [
    ":first_place:",
    ":second_place:",
    ":third_place:",
    "<:4th:1219161348253159444>",
    "<:5th:1219161347082944563>",
    "<:6th:1219163724531892224>",
    "<:7th:1219163723650826260>",
    "<:8th:1219163721704931370>",
    "<:9th:1219163722455453707>",
    "<:10th:1219163725223694336>",
    "<:11th:1292341426557943878>",
]


def get_choices(param):
    if ":" in param:
        return param.split(":")[1].split("|")

    return []


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


def parse_command(user, params, args, command):
    args = [arg.lower() for arg in args]
    params = params.split(" ")
    return_args = []

    for i, param in enumerate(params):
        required = param.startswith("[") and param.endswith("]")
        if required:
            param = param[1:-1]
        param_name = param.split(":")[0]

        missing = len(args) < i + 1
        default = None

        if missing and "username" not in param_name:
            if required:
                return errors.missing_argument(command)
            choices = get_choices(param)
            choice = None
            if choices:
                choice = choices[0]
                if param_name in ["duration", "number", "int", "text_id"]:
                    choice = int(choice)
            elif param_name == "text_id":
                choice = recent.text_id
            return_args.append(choice)


        elif param_name == "username":
            username = user["username"]

            if not missing and args[i] != "me":
                username = args[i]
            if not username:
                return errors.missing_argument(command)

            return_args.append(username)

        elif param_name == "date":
            if missing:
                return_args.append(dates.now())
            else:
                date = dates.parse_date(args[i])
                if not date:
                    return errors.invalid_date()
                return_args.append(date)

        elif param_name == "duration":
            try:
                seconds = parse_duration_string(default if missing else args[i])
            except ValueError:
                return errors.invalid_duration_format()

            return_args.append(seconds)

        elif param_name == "text_id":
            if missing or args[i] == "^":
                text_id = recent.text_id
            else:
                text_id = args[i]

            return_args.append(text_id)

        elif param_name in ["number", "int"]:
            try:
                value = parse_value_string(default if missing else args[i])
            except (ValueError, TypeError):
                return errors.invalid_number_format()

            if "int" in param_name:
                value = int(value)

            return_args.append(value)

        else:
            choices = get_choices(param)

            if missing:
                choice = choices[0]
            else:
                choice = get_category(choices, args[i])
            if not choice:
                return errors.invalid_choice(param_name, choices)

            return_args.append(choice)

    return return_args


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


def get_time_travel_date_range_string(start_date, end_date):
    if not end_date:
        return f"{get_display_date(start_date)} - Present"
    elif start_date:
        return get_display_date_range(start_date, end_date)
    else:
        return f"Past - {get_display_date(end_date)}"


def get_era_string(user):
    start_date = user["start_date"]
    end_date = user["end_date"]
    if not start_date and not end_date:
        return ""
    if start_date:
        start_date = datetime.fromtimestamp(start_date, tz=timezone.utc)
    if end_date:
        end_date = datetime.fromtimestamp(end_date, tz=timezone.utc)

    return f"-# <:galaxy:1292423577345196176> {get_time_travel_date_range_string(start_date, end_date)}"


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
    if not durations:
        raise ValueError

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


def escape_discord_format(string):
    return (string
            .replace("*", "\\*")
            .replace("_", "\\_")
            .replace("~", "\\~")
            .replace("`", ""))


def truncate_clean(text, max_chars):
    if len(text) <= max_chars:
        return escape_discord_format(text)
    if len(text.split(" ")) == 1:
        return text[:max_chars] + "..."

    substring = text[:max_chars]
    while True:
        if substring[-2].isalnum() and not substring[-1].isalnum():
            break
        substring = substring[:-1]
    substring = substring[:-1]
    substring += "..."

    return escape_discord_format(substring)


def text_description(text, universe="play"):
    if "text_id" not in text:
        text["text_id"] = text["id"]
    quote = text["quote"]
    words = len(quote.split(" "))
    chars = len(quote)
    quote = truncate_clean(quote, 1000)

    return (f"**Text** - [#{text['text_id']}]"
            f"({urls.trdata_text(text['text_id'], universe)}) - "
            f"{words:,} words - {chars:,} characters\n"
            f'"{quote}"')


def get_discord_id(string):
    if ((string.startswith("<@") and string.endswith(">") and "&" not in string)
            or (string.isnumeric() and 17 <= len(string) <= 19)):
        id = string.translate(string.maketrans("", "", "<@>"))
        return id

    return None


def discord_timestamp(timestamp, style="R"):
    return f"<t:{int(timestamp)}:{style}>"


def rank(number):
    if 1 <= number <= 11:
        return rank_emojis[number - 1]

    return str(number)


def race_id(username, number):
    return f"{username}|{number}"


def get_segments(text, n=None):
    if not n:
        n = round(len(text) / 10)
        if n > 10:
            n = 10
    words = text.split(" ")
    word_count = len(words)
    if word_count <= n or len(text) <= 60:
        full_words = [word + " " for word in words[:-1]]
        full_words.append(words[-1])
        return full_words

    segments = []
    line_size = len(text) / n
    for i in range(n):
        start = round(line_size * i)
        end = round(line_size * (i + 1))
        segments.append(text[start:end])

    full_words = []
    for i in range(len(segments)):
        segment = segments[i]
        if i == len(segments) - 1:
            full_words.append(segment)
            break

        original_segment = segment
        original_next_segment = segments[i + 1]
        prev_space = segment.rfind(" ")
        drop_chars = len(segment) - prev_space - 1
        add_chars = segments[i + 1].find(" ") + 1
        if i == 0 or drop_chars >= add_chars:
            try:
                while segment[-1] != " ":
                    segment += segments[i + 1][0]
                    segments[i + 1] = segments[i + 1][1:]
            except IndexError:
                segment = original_segment
                segments[i + 1] = original_next_segment
                try:
                    while segment[-1] != " ":
                        segments[i + 1] = segment[-1] + segments[i + 1]
                        segment = segment[:len(segment) - 1]
                except:
                    return get_segments(text, n - 1)
        else:
            try:
                while segment[-1] != " ":
                    segments[i + 1] = segment[-1] + segments[i + 1]
                    segment = segment[:len(segment) - 1]
            except:
                segment = original_segment
                segments[i + 1] = original_next_segment
                try:
                    while segment[-1] != " ":
                        segment += segments[i + 1][0]
                        segments[i + 1] = segments[i + 1][1:]
                except IndexError:
                    return get_segments(text, n - 1)

        full_words.append(segment)

    words_1 = full_words[0][:-1].split(" ")
    words_2 = full_words[1][:-1].split(" ")

    if len(words_1) == 3 and len(words_2) == 1:
        full_words[0] = f"{words_1[0]} {words_1[1]} "
        full_words[1] = f"{words_1[-1]} {words_2[0]} "

    return full_words


def get_date_query_string(start_date, end_date):
    start_string = f"AND timestamp >= {start_date}" if start_date else ""
    end_string = f"AND timestamp < {end_date}" if end_date else ""

    return start_string + end_string


def format_expression(num):
    if num == float("inf"):
        return "∞"
    elif num == int(num):
        return f"{(int(num)):,}"
    elif abs(num) >= 0.01:
        return f"{num:,.2f}"
    else:
        formatted = f"{num:.100f}"
        index = 3
        for digit in formatted[2:]:
            index += 1
            if digit != "0":
                break
        return formatted[:index]


def get_file_name(title, user, username):
    file_name = title
    start_date = user["start_date"]
    end_date = user["end_date"]
    if start_date:
        file_name += f"_{int(start_date)}"
    if end_date:
        file_name += f"_{int(end_date)}"
    file_name += f"_{username}.png"

    return file_name
