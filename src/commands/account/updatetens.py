import asyncio
import math

from discord import Embed
from discord.ext import commands

import database.main.text_results as text_results
import database.main.users as users
from api.users import get_stats
from commands.account.download import run as download
from commands.stats.stats import get_args
from commands.locks import tens_lock
from config import bot_owner
from database.main.alts import get_alts
from database.bot.users import get_user
from tasks import update_top_tens
from utils import errors, embeds, strings, colors

command = {
    "name": "updatetens",
    "aliases": ["ut"],
    "description": "Attempts to force update any outdated top tens for a user",
    "parameters": "[username]",
    "usages": ["updatetens mth_quitless"],
    "multiverse": False,
    "temporal": False,
}


class UpdateTens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def updatetens(self, ctx, *args):
        if tens_lock.locked():
            return await ctx.send(embed=Embed(
                title=f"Update In Progress",
                description=f"Please wait until the current update has finished",
                color=colors.warning,
            ))

        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username = result

        if username == "all" and ctx.author.id == bot_owner:
            async with tens_lock:
                text_count = text_results.get_count()
                await ctx.send(embed=Embed(
                    title="Top Tens Update Request",
                    description=f"Updating {text_count:,} top tens",
                    color=user["colors"]["embed"],
                ))

                await update_top_tens()

                await ctx.send(embed=Embed(
                    title="Update Complete",
                    description=f"Finished updating all top tens",
                    color=user["colors"]["embed"],
                ), content=f"<@{ctx.author.id}>")

                return

        async with tens_lock:
            await run(ctx, user, username)


async def run(ctx, user, username):
    api_stats = await get_stats(username)
    if api_stats["disqualified"]:
        await download(racer=api_stats)
        text_results.delete_user_results(username)
        return await ctx.send(embed=Embed(
            title="Top Tens Update Request",
            description=f"Deleted top tens for banned user {strings.escape_formatting(username)}",
            color=user["colors"]["embed"],
        ))

    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    text_bests = users.get_text_bests(username, text_pool=user["settings"]["text_pool"])
    top_10s = text_results.get_top_10s()
    alts = get_alts()
    outdated_texts = []

    for text_id, wpm in text_bests:
        top_10 = top_10s[text_id]
        alt_higher = False
        if not any(score["username"] == username for score in top_10):
            if username in alts:
                for alt_username in alts[username]:
                    alt_score = next((score for score in top_10 if score["username"] == alt_username), None)
                    if alt_score and alt_score["wpm"] > wpm:
                        alt_higher = True
                        break
            if not alt_higher:
                difference = top_10[-1]["wpm"] - wpm
                if difference < 0:
                    outdated_texts.append(text_id)

    username = strings.escape_formatting(username)

    if len(outdated_texts) == 0:
        return await ctx.send(embed=Embed(
            title="Top Tens Update Request",
            description=f"All top tens are up to date for {username}",
            color=user["colors"]["embed"],
        ))

    await ctx.send(embed=Embed(
        title="Top Tens Update Request",
        description=f"Updating {len(outdated_texts):,} top tens for {username}\n"
                    f"This should take {math.ceil(len(outdated_texts) / 60)} minutes",
        color=user["colors"]["embed"],
    ))

    for text_id in outdated_texts:
        await text_results.update_results(text_id)
        await asyncio.sleep(1)

    await ctx.send(embed=Embed(
        title="Update Complete",
        description=f"Finished updating top tens for {username}",
        color=user["colors"]["embed"],
    ), content=f"<@{ctx.author.id}>")


async def setup(bot):
    await bot.add_cog(UpdateTens(bot))
