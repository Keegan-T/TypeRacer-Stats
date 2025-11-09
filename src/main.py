import asyncio
import glob
import os

import discord
from aiohttp import ClientConnectionError, ClientResponseError
from discord import Embed, DiscordServerError
from discord.ext import commands, tasks
from requests.exceptions import SSLError

import records
from api.core import start_session
from commands.checks import ban_check
from config import prefix, bot_token, staging, welcome_message, bot_owner, typeracer_stats_channel_id
from database.bot.users import get_user_ids, get_total_commands, update_commands
from database.main.text_results import import_users
from database.main.typing_logs import compress_logs
from database.main.users import delete_expired_users
from tasks import import_competitions, update_important_users, update_top_tens, update_texts, demolish_cheaters
from utils import errors, colors, dates
from utils.logging import get_log_message, log, log_error

bot = commands.Bot(command_prefix=prefix, case_insensitive=True, intents=discord.Intents.all())
bot.remove_command("help")
bot.add_check(ban_check)

total_commands = sum(get_total_commands().values())
users = get_user_ids()


@bot.event
async def on_ready():
    await start_session()
    await bot.load_extension("web_server.server")

    if not staging:
        loops.start()

    log("Bot ready.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return

    elif isinstance(error, (commands.ExpectedClosingQuoteError, commands.UnexpectedQuoteError,
                            commands.InvalidEndOfQuotedStringError)):
        return await ctx.send(embed=errors.unexpected_quote())

    elif isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(embed=errors.command_cooldown(dates.now().timestamp() + error.retry_after))

    elif isinstance(error, commands.CommandInvokeError):
        original = error.original

        if isinstance(original, (ConnectionError, ClientConnectionError, SSLError)):
            return await ctx.send(embed=errors.typeracer_connection_error())
        elif isinstance(original, DiscordServerError):
            return await ctx.send(embed=errors.discord_connection_error())
        elif isinstance(original, ClientResponseError):
            if original.status == 429:
                retry_after = original.headers.get("Retry-After")
                if retry_after:
                    return await ctx.send(embed=errors.rate_limit_exceeded(int(retry_after)))
                return await ctx.send(embed=errors.rate_limit_exceeded())
            else:
                return await ctx.send(embed=errors.api_error(original.status))
        elif "or fewer in length" in str(error):
            return await ctx.send(embed=errors.embed_limit_exceeded())
        elif "Large query" in str(error):
            return await ctx.send(embed=errors.large_query_in_progress())

        if isinstance(original, discord.Forbidden):
            return log(f"Failed to send a message in <#{ctx.channel.id}>. Missing permissions.")

    log_message = get_log_message(ctx.message)
    log_error(log_message, error)

    await ctx.send(embed=errors.unexpected_error())


@bot.event
async def on_message(message):
    try:
        if message.guild.id == 703605179433484289 and message.channel.id != 1397687954117361745: # Ignore TypeGG channels
            return
    except:
        pass

    if message.content.startswith(prefix) and not message.author.bot and not staging:
        log_message = get_log_message(message)
        log(log_message)
        user_id = message.author.id
        if user_id not in users:
            users.append(user_id)
            if not message.content.startswith(prefix + "link"):
                return await message.reply(content=welcome_message)

    await bot.process_commands(message)


@bot.event
async def on_command_completion(ctx):
    global total_commands
    if not staging:
        update_commands(ctx.author.id, ctx.command.name)
    total_commands += 1
    if total_commands % 50_000 == 0:
        await celebrate_milestone(ctx, total_commands)


async def celebrate_milestone(ctx, milestone):
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
    now = dates.now()
    if now.hour == 4 and now.minute == 0:
        try:
            await import_competitions()
            await update_important_users()
            await records.update_all(bot)
            await delete_expired_users()
            await update_texts()
            await compress_logs()
            await import_users()
            await demolish_cheaters()
            if now.day == 1:
                await update_top_tens()
        except Exception as error:
            log_error("Task Failed", error)


async def load_commands():
    for dir in os.listdir("./commands"):
        if not dir.startswith("_") and os.path.isdir(os.path.join("./commands", dir)):
            for file in os.listdir(f"./commands/{dir}"):
                if file.endswith(".py") and not file.startswith("_"):
                    await bot.load_extension(f"commands.{dir}.{file[:-3]}")


def clear_image_cache():
    images = glob.glob("*.png")
    for file in images:
        os.remove(file)


async def main():
    clear_image_cache()
    await load_commands()
    await bot.start(bot_token)


if __name__ == "__main__":
    asyncio.run(main())
