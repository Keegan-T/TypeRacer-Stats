import tempfile
import time
import traceback

import requests

from config import bot_owner, staging, webhook
from database.bot.users import get_user

start = 0


def time_start():
    global start
    start = time.time()


def time_split():
    time_stop()
    time_start()


def time_stop():
    end = time.time() - start
    print(f"Took {end * 1000:,.0f}ms")


def get_log_message(message):
    message_link = "[DM]"
    if message.guild:
        message_id = message.id
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message_id}"

    author = message.author.id
    user = get_user(author)
    mention = "**You**" if author == bot_owner else f"<@{author}>"
    username = user["username"]
    linked_account = f" ({username})" if username else ""
    content = message.content

    return f"{message_link} {mention}{linked_account}: `{content}`"


def log(message, file=None):
    if staging:
        return print(message)

    if file:
        return requests.post(webhook, data={"content": message}, files={"file": file})

    requests.post(webhook, json={"content": message})


def log_error(command_message, error):
    if staging:
        return traceback.print_exception(type(error), error, error.__traceback__)

    log_message = f"<@{bot_owner}>\n{command_message}\n"
    error_traceback = traceback.format_exception(type(error), error, error.__traceback__)
    traceback_string = "".join([line for line in error_traceback])

    if len(traceback_string) >= 1800:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=True) as temp_file:
            temp_file.write(traceback_string)
            temp_file.flush()
            temp_file.seek(0)
            log(log_message, temp_file)

    log_message += f"```ansi\n\u001B[2;31m{traceback_string}\u001B[0m```"
    log(log_message)
