import math
import re
from collections import defaultdict

shift_keys = "~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:\"ZXCVBNM<>?"


def set_difficulties(text_list):
    word_freq = defaultdict(int)
    bigram_freq = defaultdict(int)

    for text in text_list:
        quote = text["quote"]
        words = re.sub(r"[^\w\s'-]", "", quote.lower()).split()
        if not words:
            words = ["a"]
        text["words"] = words
        pairs = [quote[i:i + 2] for i in range(len(quote) - 1)]
        if not pairs:
            pairs = ["th"]
        text["pairs"] = pairs

        for word in words:
            word_freq[word] += 1
        for pair in pairs:
            bigram_freq[pair] += 1

    def rank_frequency(freq_dict):
        ranked = {}
        current_rank = 0
        previous_frequency = None
        for item, freq in sorted(freq_dict.items(), key=lambda x: -x[1]):
            if freq != previous_frequency:
                current_rank += 1
            ranked[item] = current_rank
            previous_frequency = freq
        return ranked

    word_ranks = rank_frequency(word_freq)
    bigram_ranks = rank_frequency(bigram_freq)

    for text in text_list:
        quote = text["quote"]
        words = text["words"]
        pairs = text["pairs"]
        length = len(quote)
        short_factor = min(1, math.log(length) / math.log(150))

        text["word_score"] = sum([word_ranks[word] for word in words]) / len(words) * short_factor
        text["bigram_score"] = sum([bigram_ranks[pair] for pair in pairs]) / len(pairs) * short_factor

        text["repeat_score"] = sum(quote[i] == quote[i + 1] for i in range(length - 1)) / length * short_factor
        text["length_score"] = math.log2(length)

        quote += " "
        shift_weight = 0

        i = 0
        while i < len(quote) - 2:
            c1, c2, c3 = quote[i:i + 3]
            if c2 == " ":
                if (c1 in shift_keys) != (c3 in shift_keys):
                    shift_weight += 0.25
                i += 1
            else:
                if (c1 in shift_keys) != (c2 in shift_keys):
                    shift_weight += 1
            i += 1

        if quote[0] in shift_keys and quote[1] not in shift_keys:
            if quote[1] == " ":
                shift_weight -= 0.25
            else:
                shift_weight -= 1

        text["shift_score"] = shift_weight / length * short_factor

    for key in ("word_score", "bigram_score", "shift_score", "repeat_score", "length_score"):
        max_val = max(text[key] for text in text_list)
        for text in text_list:
            if max_val > 0:
                text[key] /= max_val

    for text in text_list:
        difficulty = (
                text["word_score"] * 0.2
                + text["bigram_score"] * 0.2
                + text["shift_score"] * 0.4
                + text["repeat_score"] * 0.2
                + text["length_score"] * 0.7
        )
        text["difficulty"] = difficulty

    return text_list
