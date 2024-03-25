from discord import Embed

import utils
from colors import error
from config import prefix

def missing_param(info):
    return Embed(
        title="Missing Parameters",
        description=f"Command parameters:\n"
                    f"`{prefix}{info['name']} {info['parameters']}`\n"
                    f"Example usage:\n" +
                    "\n".join([f"`{prefix}{usage}`" for usage in info['usages']]),
        color=error,
    )

def invalid_param(info):
    return Embed(
        title="Invalid Parameters",
        description=f"Command parameters:\n"
                    f"`{prefix}{info['name']} {info['parameters']}`\n"
                    f"Example usage:\n" +
                    "\n".join([f"`{prefix}{usage}`" for usage in info['usages']]),
        color=error,
    )

def invalid_option(param, options):
    return Embed(
        title="Invalid Parameter",
        description=f"Parameter `{param}` can only be:\n" +
                    "\n".join([f"`{option}`" for option in options]),
        color=error,
    )

def closing_quote():
    return Embed(
        title="Expected Closing Quote",
        description="Command parameter is missing a closing quote",
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

def no_races():
    return Embed(
        title="No Races Found",
        description="This user has not completed any races",
        color=error,
    )

def import_required(username):
    username = username.replace("`", "")
    return Embed(
        title="Import Required",
        description=f"Must `{prefix}import {username}` to use this command",
        color=error,
    )

def race_not_found():
    return Embed(
        title="Race Not Found",
        description="Details for this race are unavailable",
        color=error,
    )

def invalid_duration_format():
    return Embed(
        title="Invalid Duration",
        description="Invalid duration format. Accepted formats:\n"
                    "`1d`\n"
                    "`12h30m`\n"
                    "`2d 12h 30m 15.5s`",
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

def command_cooldown(remaining_time):
    return Embed(
        title="Command On Cooldown",
        description=f"Please wait {remaining_time:,.2f}s before running the command again",
        color=error,
    )

def unknown_text():
    return Embed(
        title="Unknown Text",
        description="Not a recognized text ID",
        color=error,
    )