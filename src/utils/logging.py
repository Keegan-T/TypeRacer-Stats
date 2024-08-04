import time
import traceback

import requests

from config import bot_owner, staging, webhook
from database.bot_users import get_user

start = 0


def time_start():
    global start
    start = time.time()


def time_split():
    time_end()
    time_start()


def time_end():
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


def log(message):
    if staging:
        return print(message)

    requests.post(webhook, json={"content": message})


def log_error(log_message, error):
    if staging:
        return traceback.print_exception(type(error), error, error.__traceback__)

    error_traceback = traceback.format_exception(type(error), error, error.__traceback__)

    log(
        f"<@{bot_owner}>\n"
        f"{log_message}\n"
        f"```ansi\n\u001B[2;31m{''.join([line for line in error_traceback])}\u001B[0m```"
    )
