from discord import Embed
from discord.ext import commands
import errors
import utils
from database.bot_users import get_user
import database.users as users

info = {
    "name": "textbests",
    "aliases": ["tb"],
    "description": "Displays a user's text best average and their best/worst quotes\n"
                   "Providing `n` will display the average of the user's top n texts",
    "parameters": "[username] <n>",
    "usages": ["textbests keegant", "textbests charlieog 100"],
    "import": True,
}


class TextBests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def textbests(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, n = await get_params(ctx, user, params, info)
        except ValueError:
            return

        await run(ctx, user, username, n)


async def get_params(ctx, user, params, command=info):
    username = user["username"]
    n = 100_000

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        try:
            n = utils.parse_value_string(params[1])
        except ValueError:
            await ctx.send(embed=errors.invalid_number_format())
            raise ValueError

    if n < 1:
        return await ctx.send(embed=errors.greater_than(0))

    if not username:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    return username.lower(), n


async def run(ctx, user, username, n):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    text_bests = users.get_text_bests(username, race_stats=True)[:n]
    texts_typed = len(text_bests)
    average = sum(text["wpm"] for text in text_bests) / texts_typed

    limit = 5

    best = ""
    for text in text_bests[:limit]:
        quote = utils.truncate_clean(text["quote"], 60)
        best += (
            f"[{text['wpm']:,.2f} WPM]"
            f"(https://data.typeracer.com/pit/result?id=|tr:{username}|{text['number']})"
            f" - Race #{text['number']:,} - Text #{text['text_id']} - "
            f"<t:{int(text['timestamp'])}:R>\n{quote}\n\n"
        )

    worst = ""
    for text in text_bests[::-1][:limit]:
        quote = utils.truncate_clean(text["quote"], 60)
        worst += (
            f"[{text['wpm']:,.2f} WPM]"
            f"(https://data.typeracer.com/pit/result?id=|tr:{username}|{text['number']})"
            f" - Race #{text['number']:,} - Text #{text['text_id']} - "
            f"<t:{int(text['timestamp'])}:R>\n{quote}\n\n"
        )

    title = "Text Bests"
    if n < stats["texts_typed"]:
        title += f" (Top {n:,} Texts)"
    embed = Embed(
        title=title,
        description=f"**Text Best Average:** {average:,.2f} WPM\n"
                    f"**Texts Typed:** {texts_typed:,}",
        color=user["colors"]["embed"],
    )

    utils.add_profile(embed, stats)

    embed.add_field(name=f"Best {limit} Texts", value=best, inline=False)
    embed.add_field(name=f"Worst {limit} Texts", value=worst, inline=False)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TextBests(bot))
