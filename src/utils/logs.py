import re


def split_log(log):
    escapes = "".join([chr(char) for char in range(1, 32)])
    log = log.encode().decode("unicode-escape").translate(escapes)
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
    try:
        unlagged = multiplier * len(quote) / total_ms
    except ZeroDivisionError:
        unlagged = float("inf")
    try:
        adjusted = multiplier * (len(quote) - 1) / (total_ms - start)
    except ZeroDivisionError:
        adjusted = float("inf")

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
    escapes = "".join([chr(char) for char in range(1, 32)])
    typing_log = typing_log.encode().decode("unicode-escape").translate(escapes)
    typing_log = re.sub("\\t\d", "a", typing_log).split("|", 1)
    times = [int(c) for c in re.findall(r"\d+", typing_log[0])][2:]

    actions = []
    for keystroke in re.findall("\d+,(?:\d+[\+\-$].?)+,", typing_log[1]):
        chars = re.findall("(?:\d+[\+\-$].?)", keystroke)
        if chars[0][-2] == "$": chars = chars[1:] + ["0-k", chars[0]]

        for i, char in enumerate(chars):
            if i > 0:
                actions.append([char[-2], 0])
            else:
                actions.append([char[-2], int(keystroke.split(",")[0])])

    raw_times = []
    for action in actions:
        if action[0] == "+" or action[0] == "$":
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


def get_wpm_over_keystrokes(delays):
    if delays[0] == 0:
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
