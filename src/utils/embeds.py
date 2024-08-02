from discord import Embed

from utils import urls


def add_profile(embed, stats, universe="play", pfp=True):
    username = stats["username"]
    author_icon = (
        f"https://flagsapi.com/{stats['country'].upper()}/flat/64.png"
        if stats["country"]
        else "https://i.imgur.com/TgHElrb.png"
    )

    if pfp:
        embed.set_thumbnail(url=urls.profile_picture(username))

    embed.set_author(
        name=username,
        url=urls.profile(username, universe),
        icon_url=author_icon,
    )

    return embed


def add_universe(embed, universe):
    if universe != "play":
        footer_text = f"Universe: {universe}"
        if embed.footer.text:
            footer_text = f"{embed.footer.text}\n{footer_text}"
        embed.set_footer(text=footer_text)


def is_embed(result):
    return isinstance(result, Embed)
