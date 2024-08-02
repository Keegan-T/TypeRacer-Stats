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
        "texts_typed": texts_typed,
        "text_best_average": text_best_average,
        "text_wpm_total": text_wpm_total,
    }

    return text_stats
