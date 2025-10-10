import codecs
import re

from api.users import get_stats
from database.main import club_races
from utils.stats import calculate_wpm


def separate_delays(log, old=False):
    quote = []
    delays = []
    pattern = r"(-?\d+)|\x08(.)|(.)"
    if old:
        pattern = r"(\d+)|\x00(.)|(.)"

    for delay, escaped, char in re.findall(pattern, log):
        if delay:
            delays.append(max(int(delay), 0))
        else:
            quote.append(escaped or char)

    return "".join(quote), delays


def split_log(typing_log):
    separator = re.search(r"\|(\d+),(\d+),(\d+),0\+", typing_log)
    if separator:
        split = separator.span()[0]
        first_half = typing_log[:split]
        action_data = typing_log[split + 1:]
        delay_data = ",".join(first_half.split(",")[3:])
    else:
        delay_data = typing_log
        action_data = None

    return delay_data, action_data


def distribute_start_lag(delays):
    lagged_chars = 1
    for delay in delays[1:]:
        if delay > 1:
            break
        lagged_chars += 1

    distributed = delays[0] / lagged_chars
    delays[:lagged_chars] = [distributed] * lagged_chars

    return delays, lagged_chars > 1


async def get_log_details(race, get_keystrokes=False, get_typos=False):
    from api.races import get_universe_multiplier
    universe = race["universe"]
    typing_log = race["log"]
    multiplier = get_universe_multiplier(universe)
    delay_data, action_data = split_log(typing_log)
    if not action_data:
        log_details = get_old_log_stats(delay_data, race["quote"], multiplier)
    else:
        log_details = get_log_stats(delay_data, action_data, multiplier, get_typos)

    for key, value in log_details.items():
        race[key] = value

    lagged = race["wpm"]
    lagged_ms = multiplier * len(race["quote"]) / lagged if lagged > 0 else 0
    ping = round(lagged_ms) - race["duration"]
    lag = race["unlagged"] - lagged
    race["ping"] = ping
    race["lag"] = lag

    # Adding new 300 WPM races
    if universe == "play" and 300 <= race["adjusted"] <= 450:
        username = race["username"]
        stats = await get_stats(username)
        if not stats["disqualified"]:
            club_races.add_race(username, race["number"], race)

    if not get_keystrokes or not action_data:
        return race

    delays = log_details["delays"]
    race["keystroke_wpm"] = get_keystroke_wpm(delays, multiplier)
    race["keystroke_wpm_adjusted"] = get_keystroke_wpm(delays, multiplier, adjusted=True)

    if log_details.get("raw_unlagged", None):
        raw_delays = log_details["raw_delays"]
        race["keystroke_wpm_raw"] = get_keystroke_wpm(raw_delays, multiplier)
        race["keystroke_wpm_raw_adjusted"] = get_keystroke_wpm(raw_delays, multiplier, adjusted=True)

        pauseless_delays = log_details["pauseless_delays"]
        race["keystroke_wpm_pauseless"] = get_keystroke_wpm(pauseless_delays, multiplier)
        race["keystroke_wpm_pauseless_adjusted"] = get_keystroke_wpm(pauseless_delays, multiplier, adjusted=True)

    return race


def get_old_log_stats(delay_data, quote, multiplier=12000):
    delays = separate_delays(delay_data, old=True)[1]
    duration = sum(delays)
    delays, distributed = distribute_start_lag(delays)
    unlagged = multiplier * len(quote) / duration
    start = delays[0]
    adjusted = multiplier * (len(quote) - 1) / (duration - start)

    return dict(
        duration=duration,
        unlagged=unlagged,
        adjusted=adjusted,
        start=start,
        characters=len(delays),
    )


def get_log_stats(delay_data, action_data, multiplier=12000, typos=False):
    quote, delays = separate_delays(delay_data)
    duration = sum(delays)
    delays, distributed = distribute_start_lag(delays)

    # Real Speeds
    start = delays[0]
    unlagged = calculate_wpm(delays, duration, multiplier)
    adjusted = calculate_wpm(delays, duration, multiplier, start)

    details = dict(
        quote=quote,
        delays=delays,
        duration=duration,
        unlagged=unlagged,
        adjusted=adjusted,
        start=start,
        distributed=distributed,
    )

    actions = re.findall(r"\d+,(?:\d+[+\-$].?)+,", action_data)
    if typos:
        details["typos"] = get_mistakes(quote, actions)

    # Raw Speeds
    raw_delays = []
    characters = 0
    for keystroke in actions:
        delay = int(keystroke.split(",")[0])
        chars = []
        for i, char in enumerate(re.findall(r"\d+[+\-$].?", keystroke)):
            if char[-2] == "$":
                chars.append("0-k")
            elif char[-2] != "-":
                characters += 1
            chars.append(char)

        for i, char in enumerate(chars):
            if i == 1:
                delay = 0
            if char[-2] == "+" or char[-2] == "$":
                raw_delays.append(delay)
            elif raw_delays:
                raw_delays.pop()

    if sum(raw_delays) == 0:
        return details
    raw_delays = distribute_start_lag(raw_delays)[0]

    # Removing trailing delays
    while raw_delays[-1] == 0:
        raw_delays.pop()

    # Taking the fastest time per character
    for i in range(min(len(raw_delays), len(delays))):
        if raw_delays[i] > delays[i]:
            raw_delays[i] = delays[i]

    # Finding pauses
    raw_start = raw_delays[0]
    no_start = raw_delays[1:]
    average = sum(no_start) / max(len(no_start), 1)
    pauses = []
    pauseless_delays = [raw_start]
    for i, time in enumerate(no_start):
        if time < average * 5:
            pauseless_delays.append(time)
        else:
            pauseless_delays.append(average)
            pauses.append(i + 1)

    raw_duration = sum(raw_delays)
    raw_unlagged = calculate_wpm(raw_delays, raw_duration, multiplier)
    raw_adjusted = calculate_wpm(raw_delays, raw_duration, multiplier, raw_start)
    correction_time = round(duration - raw_duration)
    correction_percent = correction_time / duration if duration else 0

    pauseless_duration = sum(pauseless_delays)
    pauseless_unlagged = calculate_wpm(pauseless_delays, pauseless_duration, multiplier)
    pauseless_adjusted = calculate_wpm(pauseless_delays, pauseless_duration, multiplier, pauseless_delays[0])
    pause_time = round(raw_duration - pauseless_duration)
    pause_percent = pause_time / raw_duration if raw_duration else 0

    details.update(dict(
        raw_start=raw_start,
        raw_duration=raw_duration,
        raw_delays=raw_delays,
        raw_unlagged=raw_unlagged,
        raw_adjusted=raw_adjusted,
        correction_time=correction_time,
        correction_percent=correction_percent,
        pauseless_duration=pauseless_duration,
        pauseless_delays=pauseless_delays,
        pauseless_unlagged=pauseless_unlagged,
        pauseless_adjusted=pauseless_adjusted,
        pause_time=pause_time,
        pause_percent=pause_percent,
        pauses=pauses,
        characters=characters,
    ))

    return details


def get_keystroke_wpm(delays, multiplier, adjusted=False):
    average_wpm = []
    duration = 0

    if adjusted or delays[0] == 0:
        delays = delays[1:]
        average_wpm = [float("inf")]

    for i, delay in enumerate(delays):
        duration += delay
        wpm = multiplier * (i + 1) / duration if duration else float("inf")
        average_wpm.append(wpm)

    return average_wpm


def get_mistakes(quote, actions):
    action_list = [action.split(",", 1)[1] for action in actions]
    typos = []
    typo_flag = False
    quote_words = [word + " " for word in quote.split(" ")]
    quote_words[-1] = quote_words[-1][:-1]

    current_word_index = 0
    completed_words = []
    text_box = []

    for action in action_list:
        sub_list = re.findall(r"(\d+[+\-$].)", action)

        for sub_action in sub_list:
            operator = sub_action[-2]
            index, char = int(sub_action[:-2]), sub_action[-1]

            if operator == "+":
                text_box.insert(index, char)
            elif operator == "$":
                text_box[index] = char
            else:
                text_box.pop(index)

            current_word = quote_words[current_word_index]
            text_string = "".join(text_box)

            is_typo = text_string[:len(current_word)] != current_word[:len(text_string)]

            if is_typo and not typo_flag and operator != "-":
                typo_flag = True
                typo_index = len("".join(completed_words) + "".join(text_box)) - 1
                word = current_word.rstrip()
                typos.append((current_word_index, typo_index, word))
            elif not is_typo and typo_flag:
                typo_flag = False

        while "".join(text_box).startswith(quote_words[current_word_index]):
            completed_words.append(quote_words[current_word_index])
            current_word_index += 1
            text_box = list("".join(text_box)[len(quote_words[current_word_index - 1]):])

            if current_word_index >= len(quote_words):
                break

        if "".join(completed_words) == quote:
            break

    return typos
