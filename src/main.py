import asyncio
import os
from datetime import datetime, timezone

import discord
from aiohttp import ClientConnectionError
from discord import Embed
from discord.ext import commands, tasks
from requests.exceptions import SSLError

import records
from commands.checks import ban_check
from config import prefix, bot_token, staging, welcome_message, legacy_bot_id, bot_owner, typeracer_stats_channel_id
from database import bot_users
from database.bot_users import update_commands
from database.welcomed import get_welcomed, add_welcomed
from tasks import import_competitions, update_important_users, update_top_tens
from utils import errors, colors
from utils.logging import get_log_message, log, log_error

bot = commands.Bot(command_prefix=prefix, case_insensitive=True, intents=discord.Intents.all())
bot.remove_command("help")
bot.add_check(ban_check)

total_commands = sum(bot_users.get_total_commands().values())


@bot.event
async def on_ready():
    log("Bot ready.")
    if not staging:
        loops.start()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return

    elif isinstance(error, (commands.ExpectedClosingQuoteError, commands.UnexpectedQuoteError,
                            commands.InvalidEndOfQuotedStringError)):
        return await ctx.send(embed=errors.unexpected_quote())

    elif isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(embed=errors.command_cooldown(datetime.now().timestamp() + error.retry_after))

    elif isinstance(error, commands.CommandInvokeError):
        if isinstance(error.original, (ConnectionError, ClientConnectionError, SSLError)):
            return await ctx.send(embed=errors.connection_error())
        elif "Embed size exceeds maximum size" in str(error):
            return await ctx.send(embed=errors.embed_limit_exceeded())

        if isinstance(error.original, discord.Forbidden):
            return log(f"Failed to send a message in <#{ctx.channel.id}>. Missing permissions.")

    log_message = get_log_message(ctx.message)
    log_error(log_message, error)

    await ctx.send(embed=errors.unexpected_error())


@bot.event
async def on_message(message):
    if message.reference and message.content.startswith(prefix):
        replied_message_id = message.reference.message_id
        replied_message = await message.channel.fetch_message(replied_message_id)

        if replied_message.author == bot.user:
            await message.reply(content=f"No need to reply to me anymore!")

        elif replied_message.author.id == legacy_bot_id:
            return

    if message.content.startswith(prefix) and not staging:
        log_message = get_log_message(message)
        log(log_message)
        user_id = message.author.id
        welcomed = get_welcomed()
        if user_id not in welcomed:
            await message.reply(content=welcome_message)
            add_welcomed(user_id)
            return

    await bot.process_commands(message)


@bot.event
async def on_command_completion(ctx):
    global total_commands
    if not staging:
        update_commands(ctx.author.id, ctx.command.name)
    total_commands += 1
    if total_commands % 50_000 == 0:
        await celeberate_milestone(ctx, total_commands)


async def celeberate_milestone(ctx, milestone):
    channel = bot.get_channel(typeracer_stats_channel_id)
    await channel.send(embed=Embed(
        title="Command Milestone! :tada:",
        description=f"<@{ctx.author.id}> just ran the {milestone:,}th command!",
        color=colors.success
    ))


@bot.event
async def on_guild_join(guild):
    log(f"<@{bot_owner}>\nTypeRacer Stats joined a new server: {guild.name} ({guild.id})")


@tasks.loop(minutes=1)
async def loops():
    if datetime.now(tz=timezone.utc).hour == 4 and datetime.now(tz=timezone.utc).minute == 0:
        try:
            log("Importing competitions")
            await import_competitions()
            log("Finished importing competitions")
            log("Updating important users")
            await update_important_users()
            log("Finished updating important users")
            log(f"Updating records")
            await records.update_all(bot)
            log(f"Finished updating records")
            if datetime.now(tz=timezone.utc).day == 1:
                log(f"Updating top tens")
                await update_top_tens()
                log(f"Finished updating top tens")
        except Exception as error:
            log_error("Task Failure", error)


async def load_commands():
    for dir in os.listdir("./commands"):
        if not dir.startswith("_") and os.path.isdir(os.path.join("./commands", dir)):
            for file in os.listdir(f"./commands/{dir}"):
                if file.endswith(".py") and not file.startswith("_"):
                    await bot.load_extension(f"commands.{dir}.{file[:-3]}")


async def main():
    await load_commands()
    await bot.start(bot_token)


if __name__ == "__main__":
    asyncio.run(main())
