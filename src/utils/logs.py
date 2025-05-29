import codecs
import re

from utils.stats import calculate_wpm


def split_log(log):
    quote = []
    delays = []

    for delay, escaped, char in re.findall(r"(-?\d+)|\x08(.)|(.)", log):
        if delay:
            delays.append(int(delay))
        else:
            quote.append(escaped or char)

    return "".join(quote), delays


def distribute_start_lag(delays):
    lagged_chars = 1
    for delay in delays[1:]:
        if delay != 0:
            break
        lagged_chars += 1

    distributed = delays[0] / lagged_chars
    delays[:lagged_chars] = [distributed] * lagged_chars

    return delays, lagged_chars > 1


def get_log_details(typing_log, multiplier=12000, typos=False):
    typing_log = codecs.decode(typing_log, "unicode_escape")
    separator = re.search(r"\|(\d+),(\d+),(\d+),0\+", typing_log)
    if not separator:
        first_half = typing_log
        action_data = None
    else:
        split = separator.span()[0]
        first_half = typing_log[:split]
        action_data = typing_log[split + 1:]
    delay_data = ",".join(first_half.split(",")[3:])
    quote, delays = split_log(delay_data)

    # Real Speeds
    delays, distributed = distribute_start_lag(delays)
    start = delays[0]
    duration = sum(delays)

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

    if not action_data or duration == 0:
        return details

    actions = re.findall(r"\d+,(?:\d+[+\-$].?)+,", action_data)
    if typos:
        details["typos"] = get_typos(quote, actions)

    # Raw Speeds
    raw_delays = []
    for keystroke in actions:
        delay = int(keystroke.split(",")[0])
        chars = []
        for i, char in enumerate(re.findall(r"\d+[+\-$].?", keystroke)):
            if char[-2] == "$":
                chars.append("0-k")
            chars.append(char)

        for i, char in enumerate(chars):
            if i == 1:
                delay = 0
            if char[-2] == "+" or char[-2] == "$":
                raw_delays.append(delay)
            else:
                raw_delays.pop()

    raw_delays = distribute_start_lag(raw_delays)[0]

    # Removing trailing delays
    while raw_delays[-1] == 0:
        raw_delays.pop()

    # Taking the fastest time per character
    for i in range(min(len(raw_delays), len(delays))):
        if raw_delays[i] > delays[i]:
            raw_delays[i] = delays[i]

    # Eliminating pauses
    raw_start = raw_delays[0]
    no_start = raw_delays[1:]
    average = sum(no_start) / len(no_start)
    pauses = []
    pauseless_delays = [raw_start]
    for i, time in enumerate(no_start):
        if time < average * 3:
            pauseless_delays.append(time)
        else:
            pauseless_delays.append(average)
            pauses.append(i + 1)

    raw_duration = sum(raw_delays)
    raw_unlagged = calculate_wpm(raw_delays, raw_duration, multiplier)
    raw_adjusted = calculate_wpm(raw_delays, raw_duration, multiplier, raw_start)
    correction_time = duration - raw_duration
    correction_percent = correction_time / duration if duration else 0

    pauseless_duration = sum(pauseless_delays)
    pauseless_unlagged = calculate_wpm(pauseless_delays, pauseless_duration, multiplier)
    pauseless_adjusted = calculate_wpm(pauseless_delays, pauseless_duration, multiplier, pauseless_delays[0])
    pause_time = raw_duration - pauseless_duration
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


def get_typos(quote, actions):
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
