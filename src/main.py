import asyncio
import os
from datetime import datetime

import discord
from discord.ext import commands, tasks

from commands.checks import ban_check
from config import prefix, bot_token, staging, welcome_message, log_channel_id, legacy_bot_id
from database import records
from database.bot_users import get_user, add_user, update_commands
from tasks import import_competitions, update_important_users, update_top_tens
from utils import errors
from utils.logging import set_log_channel, get_log_message, send_message, send_log, send_error

bot = commands.Bot(command_prefix=prefix, case_insensitive=True, intents=discord.Intents.all())
bot.remove_command("help")
bot.add_check(ban_check)


@bot.event
async def on_ready():
    set_log_channel(bot.get_channel(log_channel_id))
    await send_message("Bot ready.")
    if not staging:
        loops.start()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return

    elif isinstance(error, commands.ExpectedClosingQuoteError):
        return await ctx.send(embed=errors.closing_quote())

    elif isinstance(error, commands.UnexpectedQuoteError):
        return await ctx.send(embed=errors.unexpected_quote())

    elif isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(embed=errors.command_cooldown(datetime.now().timestamp() + error.retry_after))

    log_message = get_log_message(ctx.message)
    await send_error(log_message, error)

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
        await send_log(message)

    await bot.process_commands(message)


@bot.event
async def on_command(ctx):
    user = get_user(ctx)
    if not user:
        await ctx.reply(content=welcome_message)
        add_user(ctx)


@bot.event
async def on_command_completion(ctx):
    if not staging:
        update_commands(ctx.author.id, ctx.command.name)


@tasks.loop(minutes=1)
async def loops():
    if datetime.utcnow().hour == 4 and datetime.utcnow().minute == 0:
        try:
            await send_message("Importing competitions")
            await import_competitions()
            await send_message("Finished importing competitions")
            await send_message("Updating important users")
            await update_important_users()
            await send_message("Finished updating important users")
            await send_message(f"Updating records")
            await records.update(bot)
            await send_message(f"Finished updating records")
            if datetime.utcnow().day == 1:
                await send_message(f"Updating top tens")
                await update_top_tens()
                await send_message(f"Finished updating top tens")
        except Exception as error:
            await send_error("Task Failure", error)


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
