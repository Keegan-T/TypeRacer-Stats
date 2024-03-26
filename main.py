from datetime import datetime
import discord
from discord.ext import commands, tasks
import os
import sys
import asyncio
import traceback
import utils
import errors
from config import prefix, bot_token, staging_token, bot_owner, log_channel
from database.banned import get_banned
from database import records
from database.bot_users import update_commands
from tasks import import_competitions, update_important_users, update_top_tens
from database.welcomed import get_welcomed, add_welcomed

bot = commands.Bot(command_prefix=prefix, case_insensitive=True, intents=discord.Intents.all())
bot.remove_command("help")

##### FOR DEVELOPMENT #####
staging = False
###########################


async def log_command(message):
    log = utils.command_log(message)

    logs = bot.get_channel(log_channel)
    await logs.send(log)


async def error_notify(log_message, error):
    logs = bot.get_channel(log_channel)
    error_traceback = traceback.format_exception(type(error), error, error.__traceback__)

    log_message = (
        f"<@{bot_owner}>\n"
        f"{log_message}\n"
        f"```ansi\n\u001B[2;31m{''.join([line for line in error_traceback])}\u001B[0m```"
    )

    await logs.send(log_message)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def ban_check(ctx):
    if ctx.author.id == bot_owner: return True
    return str(ctx.author.id) not in get_banned()


bot.add_check(ban_check)


##### BOT EVENTS #####

@bot.event
async def on_ready():
    print("Bot ready.")
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
        return await ctx.send(embed=errors.command_cooldown(error.retry_after))

    elif isinstance(error, commands.CommandNotFound):
        return

    log = utils.command_log(ctx)
    await error_notify(log, error)


@bot.event
async def on_message(message):
    # if message.channel.id != 1197837519090352168: return
    user_id = message.author.id
    welcomed = get_welcomed()

    if user_id in welcomed and message.reference and message.content.startswith(prefix):
        replied_message_id = message.reference.message_id
        replied_message = await message.channel.fetch_message(replied_message_id)

        if replied_message.author == bot.user:
            await message.reply(content=f"No need to reply to me anymore!")

        elif replied_message.author.id == 742267194443956334: # Prevent the bot from overlapping with the other
            return

    if message.content.startswith(prefix):
        await log_command(message)

        if "keegant" in message.content:
            return await message.reply(content="He is too powerful for now...")

    await bot.process_commands(message)

@bot.event
async def on_command(ctx):
    user_id = ctx.author.id

    welcome_message = (
        f"### Welcome to the new and improved TypeRacer Stats!\n"
        f"On release there will be various bugs and issues, if you find any please contact `@keegant`\n"
        f"`-help` to view a full list of available commands.\n"
        f"`-about` to view information about the bot.\n"
        f"[Click here](https://keegan-t.github.io/TypeRacer-Stats-Changes/) to view a comprehensive list of changes.\n"
        f"**You must link your account again!**\n"
        f"Happy typing! :slight_smile:"
    )

    welcomed = get_welcomed()

    if user_id not in welcomed:
        await ctx.reply(content=welcome_message)
        add_welcomed(user_id)

@bot.event
async def on_command_completion(ctx):
    if not staging:
        update_commands(ctx.author.id, ctx.command.name)


##### BOT TASKS #####

@tasks.loop(minutes=1)
async def loops():
    if datetime.utcnow().hour == 4 and datetime.utcnow().minute == 0:
        try:
            import_competitions()
            await update_important_users()
            await records.update(bot)
            if datetime.utcnow().day == 1:
                await update_top_tens()
        except Exception as error:
            await error_notify("Task Failure", error)


async def load_commands():
    groups = ["account", "admin", "advanced", "basic", "general", "info", "owner", "unlisted"]

    for group in groups:
        for file in os.listdir(f"./commands/{group}"):
            if file.endswith(".py") and not file.startswith("_"):
                await bot.load_extension(f"commands.{group}.{file[:-3]}")


async def start():
    await load_commands()
    if staging:
        await bot.start(staging_token)
    else:
        await bot.start(bot_token)


asyncio.run(start())
