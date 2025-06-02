from discord import Embed, File
from discord.ext import commands

from config import prefix, bot_owner
from database.bot.users import get_user, update_colors
from graphs import sample_graph
from graphs.core import plt
from utils import errors, colors, strings, files

elements = {
    "embed": "Embed",
    "background": "Plot Background",
    "graphbackground": "Graph Background",
    "axis": "Axis",
    "line": "Line",
    "text": "Text",
    "grid": "Grid",
    "raw": "Raw Speed",
}

command = {
    "name": "setcolor",
    "aliases": ["sc"],
    "description": "Allows for customization of embed and graph colors\n"
                   "[Matplotlib colormaps]"
                   "(https://matplotlib.org/stable/users/explain/colors/colormaps.html) can be used for lines\n"
                   f"`{prefix}setcolor` to view your current colors\n"
                   f"`{prefix}setcolor [discord_id]` to view someone else's colors\n"
                   f"`{prefix}setcolor reset` will reset all colors to default\n",
    "parameters": "[element] [color]",
    "usages": [
        "setcolor embed 1f51ff",
        "setcolor background white",
        "setcolor graphbackground ffffff",
        "setcolor axis lightgray",
        "setcolor line ffb600",
        "setcolor text 0",
        "setcolor grid lightgray",
        "setcolor grid off",
        "setcolor raw #ffb600",
        "setcolor @keegant",
        "setcolor reset",
    ],
}


class SetColor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def setcolor(self, ctx, *args):
        user = get_user(ctx)

        result = await get_args(ctx, user, args)
        if not result:
            return

        element, color = result
        await run(ctx, user, element, color)


async def get_args(ctx, user, args):
    if not args:
        user["discord_id"] = str(ctx.author.id)
        await view(ctx, user)
        return None

    if args[0] == "reset":
        await reset(ctx, user)
        return None

    discord_id = strings.get_discord_id(args[0])
    if discord_id:
        user = get_user(discord_id, auto_add=False)
        if not user:
            await ctx.send(embed=errors.unknown_user(discord_id))
        else:
            await view(ctx, user)
        return None

    if len(args) < 2:
        await ctx.send(embed=errors.missing_argument(command))
        return None

    element = strings.get_category(elements, args[0])
    if not element:
        await ctx.send(embed=errors.invalid_choice("element", elements.keys()))
        return None

    color = colors.parse_color(args[1])
    if color is None:
        if element == "line" and args[1] in plt.colormaps():
            color = args[1]
            if color == "keegant" and ctx.author.id != bot_owner:
                await ctx.send(embed=not_worthy())
                return None
        elif element == "grid" and args[1] == "off":
            color = "off"
        else:
            await ctx.send(embed=invalid_color())
            return None

    return element, color


async def run(ctx, user, element, color):
    embed = Embed(
        title=f"{elements[element]} Color Updated",
        color=color if element == "embed" else user["colors"]["embed"],
    )

    if element == "embed":
        user["colors"][element] = color
        update_colors(ctx.author.id, user["colors"])
        return await ctx.send(embed=embed)

    try:
        user["colors"][element] = ("#%06x" % color)
    except TypeError:
        user["colors"][element] = color

    update_colors(ctx.author.id, user["colors"])

    file_name = sample_graph.render(user)

    file = File(file_name, filename=file_name)
    embed.set_image(url=f"attachment://{file_name}")
    await ctx.send(embed=embed, file=file)

    files.remove_file(file_name)


async def view(ctx, user):
    user_colors = user["colors"]
    description = (
        f"<@{user['id']}>\n\n"
        f"**Embed:** #{hex(user_colors['embed'])[2:]}\n"
        f"**Axis:** {user_colors['axis']}\n"
        f"**Background:** {user_colors['background']}\n"
        f"**Graph Background:** {user_colors['graphbackground']}\n"
        f"**Grid:** {user_colors['grid']}\n"
        f"**Line:** {user_colors['line']}\n"
        f"**Raw Speed:** {user_colors['raw']}\n"
        f"**Text:** {user_colors['text']}"
    )

    embed = Embed(
        title=f"Bot Colors",
        description=description,
        color=user["colors"]["embed"],
    )

    await ctx.send(embed=embed)


async def reset(ctx, user):
    user["colors"] = colors.default_colors
    update_colors(ctx.author.id, user["colors"])
    file_name = sample_graph.render(user)

    embed = Embed(
        title=f"Colors Reset To Default",
        color=user["colors"]["embed"],
    )

    file = File(file_name, filename=file_name)
    embed.set_image(url=f"attachment://{file_name}")
    await ctx.send(embed=embed, file=file)

    files.remove_file(file_name)


def invalid_color():
    return Embed(
        title="Invalid Color",
        description="Failed to recognize this color",
        color=colors.error,
    )


def not_worthy():
    return Embed(
        title="Not Worthy",
        description="This colormap is reserved.",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(SetColor(bot))
