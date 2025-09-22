from discord.ext import commands

from database.bot.users import get_user, update_settings
from utils import errors
from utils.embeds import Page, Message

command = {
    "name": "settings",
    "aliases": ["set"],
    "description": "Changes your bot settings",
    "parameters": "[setting] [value]",
    "usages": [
        "settings textpool maintrack",
        "settings wpm raw",
    ],
}


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def settings(self, ctx, *args):
        user = get_user(ctx)

        if not args:
            update_settings(ctx.author.id, {"text_pool": "all", "wpm": "adjusted"})
            message = Message(
                ctx=ctx,
                user=user,
                pages=[Page(title="Settings Updated", description=f"Settings have been reset to defaults")],
            )
            return await message.send()

        if len(args) < 2:
            return await ctx.send(embed=errors.missing_argument(command))

        setting, value = args[0], args[1]

        if setting in ["textpool", "pool", "tp"]:
            setting = "text_pool"
            if value in ["maintrack", "main"]:
                value = "maintrack"
            elif value in ["all", "any"]:
                value = "all"
            else:
                return await ctx.send(embed=errors.invalid_choice("value", ["maintrack", "all"]))
        elif setting in ["wpm"]:
            metrics = ["lagged", "unlagged", "adjusted", "raw", "pauseless"]
            if value not in metrics:
                return await ctx.send(embed=errors.invalid_choice("value", metrics))
        else:
            return await ctx.send(embed=errors.invalid_choice("setting", ["textpool", "wpm"]))

        await run(ctx, user, setting, value)


async def run(ctx, user, setting, value):
    settings = user["settings"]
    settings[setting] = value
    update_settings(ctx.author.id, settings)

    pages = [
        Page(
            title="Settings Updated",
            description=f"`{setting}` has been set to `{value}`"
        )
    ]

    message = Message(
        ctx=ctx,
        user=user,
        pages=pages,
    )

    await message.send()


async def setup(bot):
    await bot.add_cog(Settings(bot))
