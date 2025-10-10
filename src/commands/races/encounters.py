import copy
import statistics

from discord import Embed
from discord.ext import commands

from database.bot.users import get_user
from database.main import users, races, texts
from graphs import match_graph, encounters_graph
from utils import errors, strings, dates, colors, urls
from utils.embeds import Page, is_embed, Message, Field

command = {
    "name": "encounters",
    "aliases": ["en"],
    "description": "Displays encounter details between two users",
    "parameters": "[username1] [username2]",
    "usages": [""],
}


class Encounters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def encounters(self, ctx, *args):
        user = get_user(ctx)
        args, user = dates.set_command_date_range(args, user)

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username1, username2 = result
        await run(ctx, user, username1, username2)


def get_args(user, args, info):
    params = "username username"

    return strings.parse_command(user, params, args, info)


def analyze_encounters(encounters, username1, username2):
    encounters = sorted(encounters, key=lambda e: e[0]["number"])

    user_stats = {
        "wpms": [], "wpms_raw": [], "wpm_diffs": [],
        "accuracy": [], "correction": [], "ranks": [],
        "wins": 0, "biggest_win": None, "win_streak": 0,
    }
    stats = {
        username1: copy.deepcopy(user_stats),
        username2: copy.deepcopy(user_stats),
        "wpm_diffs": [],
        "closest": None,
        "first_encounter": None,
        "latest_encounter": None,
        "longest_streak": 0,
    }

    current_winner = None
    current_streak = 0

    current_encounter_streak = 1
    last_number = None

    for e in encounters:
        user1, user2 = e

        if last_number is not None and user1["number"] == last_number + 1:
            current_encounter_streak += 1
        else:
            current_encounter_streak = 1
        stats["longest_streak"] = max(stats["longest_streak"], current_encounter_streak)
        last_number = user1["number"]

        if user1["wpm"] > user2["wpm"]:
            winner, loser, diff = (username1, username2, user1["wpm"] - user2["wpm"])
        elif user2["wpm"] > user1["wpm"]:
            winner, loser, diff = (username2, username1, user2["wpm"] - user1["wpm"])
        else:
            winner, loser, diff = (None, None, 0)

        if winner == current_winner:
            current_streak += 1
        else:
            current_winner = winner
            current_streak = 1 if winner else 0
        if winner:
            stats[winner]["win_streak"] = max(stats[winner]["win_streak"], current_streak)

        for username, u1, u2 in [(username1, user1, user2), (username2, user2, user1)]:
            diff = u1["wpm"] - u2["wpm"]

            stats[username]["wpms"].append(u1["wpm"])
            if u1["wpm_raw"]:
                stats[username]["wpms_raw"].append(u1["wpm_raw"])
            stats[username]["wpm_diffs"].append(diff)
            stats[username]["accuracy"].append(u1["accuracy"])
            if u1["correction_time"]:
                stats[username]["correction"].append(u1["correction_time"] / u1["total_time"])
            stats[username]["ranks"].append(u1["rank"])

            if u1["wpm"] > u2["wpm"]:
                stats[username]["wins"] += 1

            if stats[username]["biggest_win"] is None or diff > stats[username]["biggest_win"][0]:
                stats[username]["biggest_win"] = (diff, u1, u2)

            if stats["closest"] is None or abs(diff) < abs(stats["closest"][0]):
                stats["closest"] = (diff, u1, u2)

            if stats["first_encounter"] is None or u1["timestamp"] < stats["first_encounter"]:
                stats["first_encounter"] = u1["timestamp"]
            if stats["latest_encounter"] is None or u1["timestamp"] > stats["latest_encounter"]:
                stats["latest_encounter"] = u1["timestamp"]

    for user in [username1, username2]:
        stats[user]["avg_wpm"] = statistics.mean(stats[user]["wpms"])
        stats[user]["avg_wpm_raw"] = statistics.mean(stats[user]["wpms_raw"])
        stats[user]["avg_wpm_diff"] = statistics.mean(stats[user]["wpm_diffs"])
        stats[user]["avg_accuracy"] = statistics.mean(stats[user]["accuracy"])
        stats[user]["avg_correction"] = statistics.mean(stats[user]["correction"])
        stats[user]["avg_rank"] = statistics.mean(stats[user]["ranks"])

    total_wins = stats[username1]["wins"] + stats[username2]["wins"]
    stats[username1]["win_rate"] = stats[username1]["wins"] / total_wins
    stats[username2]["win_rate"] = stats[username2]["wins"] / total_wins

    return stats


async def run(ctx, user, username1, username2):
    if username1 == username2:
        return await ctx.send(embed=errors.same_username())

    if username2 == user["username"]:
        username2 = username1
        username1 = user["username"]

    universe = user["universe"]
    era_string = strings.get_era_string(user)
    text_pool = user["settings"]["text_pool"]
    wpm_metric = user["settings"]["wpm"]

    db_stats1 = users.get_user_stats(username1, universe)
    if not db_stats1:
        return await ctx.send(embed=errors.import_required(username1, universe))

    db_stats2 = users.get_user_stats(username2, universe)
    if not db_stats2:
        return await ctx.send(embed=errors.import_required(username2, universe))

    encounters = await races.get_encounters(username1, username2, universe, wpm=wpm_metric, text_pool=text_pool)
    if not encounters:
        return await ctx.send(embed=no_encounters())

    if era_string:
        start_date = user["start_date"]
        if not start_date:
            start_date = 0
        end_date = user["end_date"]
        if not end_date:
            end_date = float("inf")
        encounters = [
            en for en in encounters
            if any(start_date <= row["timestamp"] < end_date for row in en)
        ]

    stats = analyze_encounters(encounters, username1, username2)

    fields = []
    for username in [username1, username2]:
        s = stats[username]
        fields.append(Field(
            name=strings.escape_formatting(username),
            value=(
                f"**Average Speed:** {s['avg_wpm']:,.2f} WPM\n"
                f"**Accuracy:** {s['avg_accuracy']:.2%}\n"
                f"**Raw Speed:** {s['avg_wpm_raw']:,.2f} WPM\n"
                f"**Correction:** {s['avg_correction']:.2%}\n"
                f"**Wins:** {s['wins']:,} ({s['win_rate']:.2%} Win Rate)\n"
                f"{'**Biggest Win:**' if s['biggest_win'][0] >= 0 else '**Closest Loss:**'} "
                f"{s['biggest_win'][0]:,.2f} WPM\n"
                f"**Best Win Streak:** {s['win_streak']:,}\n"
                f"**Average Gain:** {s['avg_wpm_diff']:,.2f} WPM\n"
                f"**Average Rank:** {s['avg_rank']:.2f}\n"
            ),
        ))

    pages = [
        Page(
            title="Race Encounters",
            description=(
                f"**Total Encounters:** {len(encounters):,}\n"
                f"**First Encounter:** {strings.discord_timestamp(stats['first_encounter'])}\n"
                f"**Latest Encounter:** {strings.discord_timestamp(stats['latest_encounter'])}\n"
                f"**Longest Streak:** {stats['longest_streak']}"
            ),
            fields=fields,
            button_name="Stats",
        )
    ]

    for title, race_data in [
        ("Biggest Win 1", stats[username1]["biggest_win"]),
        ("Biggest Win 2", stats[username2]["biggest_win"]),
        ("Closest Race", stats["closest"]),
    ]:
        difference, u1, u2 = race_data
        if "Biggest" in title and difference < 0:
            continue
        race1 = await races.get_race(u1["username"], u1["number"], universe, get_log=True, get_keystrokes=True)
        race2 = await races.get_race(u2["username"], u2["number"], universe, get_log=True, get_keystrokes=True)
        match = [race1, race2]
        original_races = [u1, u2]
        for i, race in enumerate(match):
            if not race["wpm_raw"]:
                pages.append(Page(
                    title="Logs Not Found",
                    description=f"Log details for race `{race['username']}|{race['number']}|{universe}` are unavailable",
                    color=colors.error,
                ))
            match[i]["wpm"] = original_races[i]["wpm"]
            match[i]["keystroke_wpm"] = match[i][("keystroke_" + wpm_metric).replace("_unlagged", "")]

        match.sort(key=lambda x: -x["wpm"])
        page_title = title
        if "Biggest" in title:
            page_title = "Race Encounters - " + title[:-2] + f" ({strings.escape_formatting(match[0]['username'])})"
        text_description = strings.text_description(texts.get_text(match[0]["text_id"], universe), universe)
        description = text_description + "\n\n**Rankings**\n"

        for i, race in enumerate(match):
            racer_username = strings.escape_formatting(race["username"])
            description += (
                f"{i + 1}. {racer_username} - "
                f"[{race['wpm']:,.2f} WPM]"
                f"({urls.replay(race['username'], race['number'], universe)}) "
                f"({race['accuracy']:.2%} Acc, "
                f"{race['start']:,.0f}ms start)\n"
            )

        completed = f"\nCompleted {strings.discord_timestamp(match[0]['timestamp'])}"
        description += completed
        description = f"{'+' if difference > 0 else ''}{difference:,.2f} WPM\n\n" + description
        graph_title = f"Match Graph - {match[0]['username']} - Race #{match[0]['number']:,}"

        def render(rankings):
            return lambda: match_graph.render(
                user, rankings, graph_title, "WPM", universe,
                limit_y="*" not in ctx.invoked_with
            )

        pages.append(
            Page(page_title, description, button_name=title, render=render(match))
        )

    def render(encounters):
        return lambda: encounters_graph.render(
            user, f"Race Encounters\n{username1} vs. {username2}", encounters, universe
        )

    pages.append(Page(
        title="Race Encounters - Graph",
        description=(
            f":red_circle: {strings.escape_formatting(username1)}\n"
            f":blue_circle: {strings.escape_formatting(username2)}"
        ),
        button_name="Graph",
        render=render(encounters),
    ))

    message = Message(
        ctx=ctx,
        user=user,
        pages=pages,
        universe=universe,
        text_pool=text_pool,
        wpm_metric=wpm_metric,
    )

    await message.send()


def no_encounters():
    return Embed(
        title="No Encounters",
        description="Users do not appear in any races together",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Encounters(bot))
