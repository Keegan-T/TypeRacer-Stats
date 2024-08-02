import time

from config import bot_owner
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
    print(f"Took {end:,.2f}s")


def log_message(message):
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
