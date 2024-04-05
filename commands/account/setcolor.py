from discord import Embed, File
from discord.ext import commands
import graphs
import utils
import errors
import colors
from config import prefix
from database.bot_users import get_user, update_colors
import matplotlib.pyplot as plt

elements = {
    "embed": "Embed",
    "background": "Plot Background",
    "graphbackground": "Graph Background",
    "axis": "Axis",
    "line": "Line",
    "text": "Text",
    "grid": "Grid",
}

info = {
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
        "setcolor @keegant",
        "setcolor reset",
    ],
    "import": False,
}


class SetColor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def setcolor(self, ctx, *params):
        user = get_user(ctx)

        try:
            element, color = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, element, color)


async def get_params(ctx, user, params):
    if not params:
        user["discord_id"] = str(ctx.author.id)
        await view(ctx, user)
        raise ValueError

    if params[0] == "reset":
        await reset(ctx, user)
        raise ValueError

    discord_id = utils.get_discord_id(params[0])
    if discord_id:
        user = get_user(discord_id)
        await view(ctx, user)
        raise ValueError

    if len(params) < 2:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    element = utils.get_category(elements, params[0])
    if not element:
        await ctx.send(embed=errors.invalid_option("element", elements.keys()))
        raise ValueError

    color = utils.parse_color(params[1])
    if color is None:
        if element == "line" and params[1] in plt.colormaps():
            color = params[1]
        else:
            await ctx.send(embed=invalid_color())
            raise ValueError

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

    graphs.sample(user)

    file_name = "sample.png"
    file = File(file_name, filename=file_name)
    embed.set_image(url=f"attachment://{file_name}")
    await ctx.send(embed=embed, file=file)

    utils.remove_file(file_name)


async def view(ctx, user):
    description = (
        f"<@{user['id']}>\n\n"
        f"**Embed:** #{hex(user['colors']['embed'])[2:]}\n"
        f"**Axis:** {user['colors']['axis']}\n"
        f"**Background:** {user['colors']['background']}\n"
        f"**Graph Background:** {user['colors']['graphbackground']}\n"
        f"**Grid:** {user['colors']['grid']}\n"
        f"**Line:** {user['colors']['line']}\n"
        f"**Text:** {user['colors']['text']}"
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
    graphs.sample(user)

    embed = Embed(
        title=f"Colors Reset To Default",
        color=user["colors"]["embed"],
    )

    file_name = "sample.png"
    file = File(file_name, filename=file_name)
    embed.set_image(url=f"attachment://{file_name}")
    await ctx.send(embed=embed, file=file)

    utils.remove_file(file_name)

def invalid_color():
    return Embed(
        title="Invalid Color",
        description="Failed to recognize this color",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(SetColor(bot))
