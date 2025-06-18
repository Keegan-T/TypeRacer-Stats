from database.main import texts
from database.main.texts import filter_disabled


def calculate_points(quote, wpm):
    return (wpm / 60) * len(quote.split(" "))


def calculate_seconds(quote, wpm):
    if wpm == 0: return 0
    return (len(quote) * 12) / wpm


def calculate_wpm(delays, duration, multiplier, start=None):
    length = len(delays)
    if start:
        length -= 1
        duration -= start
    return multiplier * length / duration if duration != 0 else float("inf")


def get_text_stats(text_bests):
    text_wpm_total = 0
    for text_best in text_bests:
        text_wpm_total += text_best["wpm"]

    texts_typed = len(text_bests)
    text_best_average = text_wpm_total / texts_typed if texts_typed else 0

    text_stats = {
        "texts_typed": texts_typed,
        "text_best_average": text_best_average,
        "text_wpm_total": text_wpm_total,
    }

    return text_stats


def calculate_text_bests(race_list):
    tb_dict = {}
    for race in race_list:
        text_id = race["text_id"]
        if text_id not in tb_dict or race["wpm"] > tb_dict[text_id]["wpm"]:
            tb_dict[text_id] = race

    text_bests = sorted(tb_dict.values(), key=lambda x: x["wpm"], reverse=True)

    return filter_disabled(text_bests)


def time_travel_races(race_list, user):
    start_date = user["start_date"]
    end_date = user["end_date"]

    if not start_date and not end_date:
        return race_list

    return [
        race for race in race_list if
        (not start_date or race["timestamp"] >= start_date) and
        (not end_date or race["timestamp"] < end_date)
    ]


def calculate_performance(wpm, difficulty):
    return wpm ** 1.5 * difficulty ** 1.2


def calculate_total_performance(text_bests, text_list):
    scores = []
    for race in text_bests:
        text_id = race["text_id"]
        wpm = race["wpm"]
        difficulty = text_list[text_id]["difficulty"]
        performance = calculate_performance(wpm, difficulty)
        scores.append({**race, "performance": performance})

    scores.sort(key=lambda x: -x["performance"])
    total_performance = 0
    for i, score in enumerate(scores):
        total_performance += score["performance"] * (0.95 ** i)

    return total_performance


def calculate_text_performances(text_bests, universe="play"):
    text_dict = texts.get_texts(True, False, universe)
    min_difficulty = min(text["difficulty"] for text in text_dict.values())
    max_difficulty = max(text["difficulty"] for text in text_dict.values())
    for i in range(len(text_bests)):
        score = dict(text_bests[i])
        text_id = score["text_id"]
        wpm = score["wpm"]
        quote = text_dict[text_id]["quote"]
        text = text_dict[text_id]
        difficulty = text["difficulty"]
        performance = calculate_performance(wpm, difficulty)
        rating = ((difficulty - min_difficulty) / (max_difficulty - min_difficulty)) * 10
        score.update({
            "quote": quote,
            "performance": performance,
            "rating": rating,
        })
        text_bests[i] = score


def get_top_disjoint_windows(windows, count=10):
    top_windows = []
    used_ranges = []
    for start_index, end_index, race_count in windows:
        overlap = False
        for s, e in used_ranges:
            if not (end_index <= s or start_index >= e):
                overlap = True
                break
        if not overlap:
            top_windows.append((start_index, end_index, race_count))
            used_ranges.append((start_index, end_index))
            if len(top_windows) == count:
                break

    return top_windows
