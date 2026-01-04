from datetime import datetime

import aiohttp_jinja2

from api.races import get_universe_multiplier
from api.users import get_stats
from commands.account.download import run as download
from database.main import users, races, texts
from utils.stats import calculate_wpm
from utils.strings import get_segments


@aiohttp_jinja2.template("race.html")
async def race_page(request):
    username = request.match_info.get("username")
    race_number = request.match_info.get("number")
    universe = request.query.get("universe", "play")

    db_stats = users.get_user(username, universe)
    if not db_stats:
        raise ValueError("Import Required")

    stats = await get_stats(username, universe=universe)
    await download(racer=stats, universe=universe)

    race_number = int(race_number)
    race_info = await races.get_race(username, race_number, universe, get_log=True, get_typos=True)
    if not race_info:
        raise ValueError("Race Not Found")

    quote = texts.get_text(race_info["text_id"], universe)["quote"]

    data = {
        "username": username,
        "race_number": race_number,
        "race_number_formatted": f"{race_number:,}",
        "universe": universe,
        "date": datetime.fromtimestamp(race_info["timestamp"]).strftime("%b %d %Y, %I:%M:%S %p"),
        "points": f"{race_info["points"]:,.0f}",
        "rank": race_info["rank"],
        "racers": race_info["racers"],
        "wpm_unlagged": f"{race_info["wpm_unlagged"]:,.2f}",
        "wpm_adjusted": f"{race_info["wpm_adjusted"]:,.2f}",
        "accuracy": f"{race_info["accuracy"]:.2%}",
        "start_time": f"{race_info["start_time"] / 1000:,.3f}",
        "total_time": f"{race_info["total_time"] / 1000:,.3f}",
        "text_id": race_info["text_id"],
        "quote": quote,
    }

    if "raw_unlagged" in race_info:
        delays = race_info["delays"]
        raw_delays = race_info["raw_delays"]
        multiplier = get_universe_multiplier(universe)

        segments = build_segment_stats(delays, raw_delays, race_info["quote"], multiplier)
        graph_data = build_graph_data(segments)

        data |= {
            "raw_unlagged": f"{race_info["raw_unlagged"]:,.2f}",
            "raw_adjusted": f"{race_info["raw_adjusted"]:,.2f}",
            "correction_time": f"{race_info["correction_time"] / 1000:,.2f}",
            "correction_percent": f"{race_info["correction_percent"]:.2%}",
            "pauseless_adjusted": f"{race_info["pauseless_adjusted"]:,.2f}",
            "pause_time": f"{race_info["pause_time"] / 1000:,.2f}",
            "pause_percent": f"{race_info["pause_percent"]:.2%}",
            "characters": [char for char in quote],
            "delays": delays,
            "raw_delays": raw_delays,
            "quote": race_info["quote"],
            "processed_actions": race_info["processed_actions"],
            "typing_log": race_info["log"].replace("\x08", r"\b"),
            "graph": graph_data,
        }

    return data


def build_segment_stats(delays, raw_delays, quote, multiplier):
    text_segments = get_segments(quote)
    segments = []
    i = 0

    for text in text_segments:
        end = i + len(text)

        segment_delays = delays[i:end]
        raw_segment_delays = raw_delays[i:end]

        wpm = calculate_wpm(segment_delays, sum(segment_delays), multiplier)
        raw_wpm = calculate_wpm(raw_segment_delays, sum(raw_segment_delays), multiplier)

        segments.append({
            "text": text,
            "wpm": wpm,
            "raw_wpm": raw_wpm,
        })

        i = end

    return segments


def build_graph_data(segments):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    values = [segment["raw_wpm"] for segment in segments]

    fig, ax = plt.subplots()
    ax.bar(range(len(values)), values)
    fig.canvas.draw()

    ymax = ax.get_ylim()[1]
    max_value = max(values)
    filtered_ticks = []

    for tick in ax.get_yticks():
        filtered_ticks.append(int(tick))
        if tick >= max_value:
            break

    return {
        "segments": segments,
        "ymax": ymax,
        "yticks": filtered_ticks,
    }
