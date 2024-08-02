import asyncio
import os
import sys
import traceback
from datetime import datetime

import discord
from discord.ext import commands, tasks

from commands.checks import ban_check
from config import prefix, bot_token, bot_owner, log_channel, staging
from database import records
from database.bot_users import update_commands
from database.welcomed import get_welcomed, add_welcomed
from tasks import import_competitions, update_important_users, update_top_tens
from utils import errors, logging

sys.path.insert(0, "")

bot = commands.Bot(command_prefix=prefix, case_insensitive=True, intents=discord.Intents.all())
bot.remove_command("help")
bot.add_check(ban_check)


async def log_command(ctx):
    log = logging.log_message(ctx)
    logs = bot.get_channel(log_channel)

    await logs.send(log)


async def error_notify(log_message, error):
    logs = bot.get_channel(log_channel)
    error_traceback = traceback.format_exception(type(error), error, error.__traceback__)

    await logs.send(
        f"<@{bot_owner}>\n"
        f"{log_message}\n"
        f"```ansi\n\u001B[2;31m{''.join([line for line in error_traceback])}\u001B[0m```"
    )


@bot.event
async def on_ready():
    print("Bot ready.")
    if not staging:
        loops.start()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        user_id = ctx.author.id
        user = await bot.fetch_user(user_id)
        print(f"Check failure! {user} ({user_id}) attempted to use {ctx.command}")
        return

    elif isinstance(error, commands.ExpectedClosingQuoteError):
        return await ctx.send(embed=errors.closing_quote())

    elif isinstance(error, commands.UnexpectedQuoteError):
        return await ctx.send(embed=errors.unexpected_quote())

    elif isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(embed=errors.command_cooldown(datetime.now().timestamp() + error.retry_after))

    elif isinstance(error, commands.CommandNotFound):
        return

    elif isinstance(error, discord.errors.Forbidden):
        logs = bot.get_channel(log_channel)
        await logs.send("Missing permissions")
        return

    log = logging.log_message(ctx.message)
    if not staging:
        await error_notify(log, error)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    await ctx.send(embed=errors.unexpected_error())


@bot.event
async def on_message(message):
    user_id = message.author.id
    welcomed = get_welcomed()

    if user_id in welcomed and message.reference and message.content.startswith(prefix):
        replied_message_id = message.reference.message_id
        replied_message = await message.channel.fetch_message(replied_message_id)

        if replied_message.author == bot.user:
            await message.reply(content=f"No need to reply to me anymore!")

        elif replied_message.author.id == 742267194443956334:  # Prevent the bot from overlapping with the other
            return

    if message.content.startswith(prefix) and not staging:
        await log_command(message)

    await bot.process_commands(message)


@bot.event
async def on_command(ctx):
    user_id = ctx.author.id

    welcome_message = (
        f"### Welcome to TypeRacer Stats!\n"
        f"Run `{prefix}link [typeracer_username]` to start using the bot\n"
    )

    welcomed = get_welcomed()

    if user_id not in welcomed:
        await ctx.reply(content=welcome_message)
        add_welcomed(user_id)


@bot.event
async def on_command_completion(ctx):
    if not staging:
        update_commands(ctx.author.id, ctx.command.name)


@tasks.loop(minutes=1)
async def loops():
    if datetime.utcnow().hour == 4 and datetime.utcnow().minute == 0:
        logs = bot.get_channel(log_channel)
        try:
            await logs.send("Importing competitions")
            await import_competitions()
            await logs.send("Finished importing competitions")
            await logs.send("Updating important users")
            await update_important_users()
            await logs.send("Finished updating important users")
            await logs.send(f"Updating records")
            await records.update(bot)
            await logs.send(f"Finished updating records")
            if datetime.utcnow().day == 1:
                await logs.send(f"Updating top tens")
                await update_top_tens()
                await logs.send(f"Finished updating top tens")
        except Exception as error:
            await error_notify("Task Failure", error)


async def load_commands():
    for dir in os.listdir("./commands"):
        if not dir.startswith("_") and os.path.isdir(os.path.join("./commands", dir)):
            for file in os.listdir(f"./commands/{dir}"):
                if file.endswith(".py") and not file.startswith("_"):
                    await bot.load_extension(f"commands.{dir}.{file[:-3]}")


async def main():
    await load_commands()
    await bot.start(bot_token)


asyncio.run(main())
