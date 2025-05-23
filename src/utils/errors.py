from discord import Embed

from config import prefix
from utils import strings
from utils.colors import error, warning


def add_universe(embed, universe):
    if universe == "play":
        return

    footer_text = f"{embed.footer.text}\n" if embed.footer.text else ""
    embed.set_footer(text=footer_text + f"Universe: {universe}")


def missing_argument(info):
    return Embed(
        title="Missing Argument",
        description=f"Command parameters:\n"
                    f"`{prefix}{info['name']} {info['parameters']}`\n"
                    f"Example usage:\n" +
                    "\n".join([f"`{prefix}{usage}`" for usage in info['usages']]),
        color=error,
    )


def invalid_argument(info):
    return Embed(
        title="Invalid Argument",
        description=f"Command parameters:\n"
                    f"`{prefix}{info['name']} {info['parameters']}`\n"
                    f"Example usage:\n" +
                    "\n".join([f"`{prefix}{usage}`" for usage in info['usages']]),
        color=error,
    )


def invalid_choice(param, choices):
    return Embed(
        title="Invalid Argument",
        description=f"Parameter `{param}` can only be:\n" +
                    "\n".join([f"`{choice}`" for choice in choices]),
        color=error,
    )


def unexpected_quote():
    return Embed(
        title="Unxpected Quote",
        description="Command parameter contains an unexpected quote",
        color=error,
    )


def invalid_command():
    return Embed(
        title="Command Not Found",
        description=f"`{prefix}help` for a list of commands",
        color=error,
    )


def invalid_username():
    return Embed(
        title="Invalid Username",
        description="User does not exist",
        color=error,
    )


def no_races(universe="play"):
    embed = Embed(
        title="No Races Found",
        description="User has not completed any races",
        color=error,
    )
    add_universe(embed, universe)

    return embed


def no_races_in_range(universe):
    embed = Embed(
        title="No Races Found",
        description="User has no races in this range",
        color=error,
    )
    add_universe(embed, universe)

    return embed


def import_required(username, universe="play", time_travel=False):
    username = username.replace("`", "")
    embed = Embed(
        title="Import Required",
        description=f"Must `{prefix}import {username}` to use this command",
        color=error,
    )
    add_universe(embed, universe)

    if time_travel:
        embed.description += "\nwhile time travelling"

    return embed


def race_not_found(username, race_number, universe="play"):
    race_id = f"{username}|{race_number}"
    if universe != "play":
        race_id = f"{universe}|" + race_id

    return Embed(
        title="Race Not Found",
        description=f"Details for race `{race_id}` are unavailable",
        color=error,
    )


def logs_not_found(username, race_number, universe="play"):
    race_id = f"{username}|{race_number}"
    if universe != "play":
        race_id = f"{universe}|" + race_id

    return Embed(
        title="Logs Not Found",
        description=f"Log details for race `{race_id}` are unavailable",
        color=error,
    )


def invalid_duration_format():
    return Embed(
        title="Invalid Duration",
        description="Invalid duration format. Accepted formats:\n"
                    "`1d`\n"
                    "`12h30m`\n"
                    "`2d12h30m15.5s`",
        color=error,
    )


def invalid_number_format():
    return Embed(
        title="Invalid Number",
        description="Invalid number format. Accepted formats:\n"
                    "`10000`, `20k`, `25.5k`, `1.2m`",
        color=error,
    )


def invalid_date():
    return Embed(
        title="Invalid Date",
        description="Unrecognized date format",
        color=error,
    )


def greater_than(n):
    return Embed(
        title="Invalid Number",
        description=f"Number must be greater than {n}",
        color=error,
    )


def command_cooldown(cooldown_expiration):
    return Embed(
        title="Command On Cooldown",
        description=f"You may use the command again {strings.discord_timestamp(cooldown_expiration)}",
        color=error,
    )


def unknown_text(universe="play"):
    embed = Embed(
        title="Unknown Text",
        description="Not a recognized text ID",
        color=error,
    )
    add_universe(embed, universe)

    return embed


def unexpected_error():
    return Embed(
        title="Unexpected Error",
        description=f"An unexpected error occured",
        color=error,
    )


def command_in_use():
    return Embed(
        title=f"Command In Use",
        description=f"Please wait until the current usage has finished",
        color=warning,
    )


def large_query_in_progress():
    return Embed(
        title="Large Query In Progress",
        description="A recent command has queried a large number of races\n"
                    "Please wait until the command has finished",
        color=warning,
    )


def connection_error():
    return Embed(
        title="Connection Error",
        description="Failed to connect to the the TypeRacer servers\n"
                    "Please try again later",
        color=error,
    )


def unknown_user(user_id):
    return Embed(
        title="Unknown User",
        description=f"<@{user_id}> has never used the bot before",
        color=error,
    )


def embed_limit_exceeded():
    return Embed(
        title="Embed Limit Exceeded",
        description="The maximum number of characters\nfor an embed has been exceeded",
        color=error,
    )

def same_username():
    return Embed(
        title="Same Username",
        description="Must input two unique usernames to compare",
        color=error,
    )

def no_common_texts(universe):
    embed = Embed(
        title="No Data",
        description="Users do not have any texts in common",
        color=error,
    )
    add_universe(embed, universe)

    return embed