import re


def escape_characters(string):
    escapes = "".join([chr(char) for char in range(1, 32)])

    return string.encode().decode("unicode-escape").translate(escapes)


def split_log(log):
    log = escape_characters(log)
    quote = ""
    delays = []

    current_num = ""
    i = 0
    while i < len(log):
        char = log[i]
        if char.isdigit() or (char == "-" and log[i - 1] != "\t"):
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


def get_raw_speeds(typing_log, times):
    typing_log = escape_characters(typing_log)
    typing_log = re.sub(r"\t\d", "a", typing_log).split("|", 1)
    raw_times = []

    for keystroke in re.findall("\d+,(?:\d+[+\-$].?)+,", typing_log[1]):
        delay = int(keystroke.split(",")[0])

        chars = []
        for i, char in enumerate(re.findall("(?:\d+[+\-$].?)", keystroke)):
            if char[-2] == "$":
                chars.append("0-k")
            chars.append(char)

        for i, char in enumerate(chars):
            if i == 1:
                delay = 0
            if char[-2] == "+" or char[-2] == "$":
                raw_times.append(delay)
            else:
                raw_times.pop()

    while raw_times[-1] == 0: # Removing trailing delays
        raw_times.pop()

    if raw_times[0] == 0: # Preventing zero starts
        for i in range(1, len(raw_times)):
            if raw_times[i] > 0:
                raw_times.insert(0, raw_times.pop(i))
                break

    for i in range(len(raw_times)): # Taking the fastest time per character
        if raw_times[i] > times[i]:
            raw_times[i] = times[i]

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

def get_typos(quote, action_data):
    action_data = escape_characters(action_data)
    action_data = re.sub(r"\t\d", "a", action_data)
    actions = re.findall(r"\d+,(?:\d+[+\-$].?)+,", action_data)
    action_list = [action.split(",", 1)[1] for action in actions]

    typos = {}
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

            if text_string[:len(current_word)] != current_word[:len(text_string)]:
                if current_word_index not in typos:
                    typo_index = len("".join(completed_words) + "".join(text_box)) - 1
                    typos[current_word_index] = f"{current_word[:-1]},{typo_index}"

        while "".join(text_box).startswith(quote_words[current_word_index]):
            completed_words.append(quote_words[current_word_index])
            current_word_index += 1
            text_box = list("".join(text_box)[len(quote_words[current_word_index - 1]):])

            if current_word_index >= len(quote_words):
                break

        if "".join(completed_words) == quote:
            break

    typo_list = []
    for typo in typos.values():
        word, index = typo.rsplit(",", 1)
        typo_list.append([int(index), word])

    return typo_list