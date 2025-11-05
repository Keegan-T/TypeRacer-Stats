import tempfile

from discord import File
from discord.ext import commands

from api.users import get_stats
from commands.account.download import run as download
from commands.races.realspeed import get_args
from database.bot.users import get_user
from database.main import users
from database.main.typing_logs import get_log
from utils import errors, strings
from utils.embeds import Page, is_embed, Message

command = {
    "name": "typinglog",
    "aliases": ["log"],
    "description": "Displays the typing log for a given username and race number.",
    "parameters": "[username] <race_number>",
    "usages": ["log poem 100000"],
}


class TypingLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def typinglog(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command, ctx.channel.id)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, race_number, universe = result
        await run(ctx, user, username, race_number, universe)


async def run(ctx, user, username, race_number, universe):
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    api_stats = await get_stats(username, universe=universe)
    if race_number < 1:
        race_number = api_stats["races"] + race_number

    await download(racer=api_stats, universe=universe)
    typing_log = await get_log(username, race_number, universe)

    title = f"{username} - Race #{race_number:,} (Universe: {universe})"

    if len(typing_log) > 1900:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as tmp:
            tmp.write(typing_log)
            tmp.seek(0)
            await ctx.send(content=title, file=File(tmp.name, filename=f"typing_log_{username}_{race_number}_{universe}.txt"))
    else:
        await ctx.send(content=f"{title}\n```{typing_log}```")


async def setup(bot):
    await bot.add_cog(TypingLog(bot))
