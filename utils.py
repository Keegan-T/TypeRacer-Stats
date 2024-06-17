from discord import Embed
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser
from dateutil.relativedelta import relativedelta
import matplotlib.colors as mcolors
import errors
import urls
import time
from database.bot_users import get_user
from config import bot_owner
import commands.recent as recent
import os


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


def get_log_details(log, multiplier=12000):
    quote, delays = split_log(log)

    total_ms = sum(delays)
    start = delays[0]
    unlagged = multiplier * len(quote) / total_ms
    adjusted = multiplier * (len(quote) - 1) / (total_ms - start)

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
    typing_log = typing_log.encode().decode('unicode-escape').translate(escapes)
    typing_log = re.sub('\\t\d', 'a', typing_log).split('|', 1)
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
    ["best"],
    ["worst"],
    ["random", "rand", "r"],
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
    if ((string.startswith("<@") and string.endswith(">") and "&" not in string)
            or (string.isnumeric() and 17 <= len(string) <= 19)):
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


def command_log_message(message):
    message_link = "[DM]"
    if message.guild:
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"

    user = get_user(message.author.id)
    author = message.author.id
    mention = "**You**" if author == bot_owner else f"<@{author}>"
    username = user["username"]
    linked_account = f" ({username})" if username else ""
    message = message.content

    return f"{message_link} {mention}{linked_account}: `{message}`"


def error_log_message(ctx):
    message_link = "[DM]"
    if ctx.guild:
        message_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"

    user = get_user(ctx.author.id)
    author = ctx.author.id
    mention = "**You**" if author == bot_owner else f"<@{author}>"
    username = user["username"]
    linked_account = f" ({username})" if username else ""
    message = ctx.message.content

    return f"{message_link} {mention}{linked_account}: `{message}`"


def race_id(username, number):
    return f"{username}|{number}"


def get_race_link_info(link):
    try:
        splat = link.replace("%7C", "|").split("|")
        universe = splat[-3].split("?id=")[1]
        if not universe:
            universe = "play"
        username = splat[-2][3:]
        race_number = int(splat[-1].split("&")[0])

        return [username, race_number, universe]
    except Exception:
        return None


def get_universe_multiplier(universe):
    if universe == "lang_ko":
        return 24000
    elif universe in ["lang_zh", "lang_zh-tw", "new_lang_zh-tw", "lang_ja"]:
        return 60000
    return 12000


def remove_file(file_name):
    try:
        os.remove(file_name)
    except (FileNotFoundError, PermissionError):
        return
    except Exception:
        raise Exception


def get_choices(param):
    if ":" in param:
        return param.split(":")[1].split("|")

    return []


def get_url_info(url):
    result = urlparse(url)
    if not (result.netloc and result.scheme):
        return None
    try:
        parts = url.replace("%7C", "|").split("|")
        universe = parts[-3].split("?id=")[1]
        if not universe:
            universe = "play"
        username = parts[-2][3:]
        race_number = int(parts[-1].split("&")[0])

        return username, race_number, universe
    except Exception:
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
                return_args.append(datetime.now(timezone.utc))
            else:
                try:
                    date = parser.parse(args[i])
                    return_args.append(date)
                except ValueError:
                    return errors.invalid_date()

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


def is_embed(result):
    return isinstance(result, Embed)
