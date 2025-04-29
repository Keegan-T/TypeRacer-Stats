from discord import Embed, ButtonStyle
from discord.ui import View, Button

from config import web_server
from utils import urls, strings


class Message(View):
    def __init__(self, ctx, title, descriptions, user, profile=None, universe=None, show_pfp=True):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.era_string = strings.get_era_string(user)

        if isinstance(descriptions, str):
            descriptions = [descriptions]

        self.embeds = []
        for i, description in enumerate(descriptions):
            embed = Embed(
                title=title,
                description=description,
                color=user["colors"]["embed"],
            )
            if profile:
                self.add_profile(embed, profile, show_pfp)
            if universe:
                self.add_universe(embed, universe)
            if len(descriptions) > 1:
                update_footer(embed, f"Page {i + 1} of {len(descriptions)}")
            self.embeds.append(embed)

        self.page = 1
        self.pages = len(self.embeds)
        if self.pages > 1:
            self.add_navigation_buttons()
            self.update_buttons()

    def add_profile(self, embed, stats, show_pfp=True):
        username = stats["username"]
        author_icon = (
            f"{web_server}/images/flags/{stats['country'].upper()}.png"
            if stats["country"]
            else f"{web_server}/images/silhouette.png"
        )

        if show_pfp:
            embed.set_thumbnail(url=urls.profile_picture(username))

        embed.set_author(
            name=username,
            url=urls.profile(username),
            icon_url=author_icon,
        )

    def add_universe(self, embed, universe):
        if universe == "play":
            return

        if embed.author.url:
            embed.set_author(
                name=embed.author.name,
                url=f"{embed.author.url}&universe={universe}",
                icon_url=embed.author.icon_url,
            )

        update_footer(embed, f"Universe: {universe}")

    def update_buttons(self):
        self.children[0].disabled = self.page == 1
        self.children[1].disabled = self.page == 1
        self.children[2].disabled = self.page == len(self.embeds)
        self.children[3].disabled = self.page == len(self.embeds)

    def add_navigation_buttons(self):
        self.first_button = Button(label="\u25c0\u25c0", style=ButtonStyle.secondary)
        self.previous_button = Button(label="\u25c0", style=ButtonStyle.primary)
        self.next_button = Button(label="\u25b6", style=ButtonStyle.primary)
        self.last_button = Button(label="\u25b6\u25b6", style=ButtonStyle.secondary)

        self.first_button.callback = self.first
        self.previous_button.callback = self.previous
        self.next_button.callback = self.next
        self.last_button.callback = self.last

        self.add_item(self.first_button)
        self.add_item(self.previous_button)
        self.add_item(self.next_button)
        self.add_item(self.last_button)

    async def first(self, interaction):
        if self.page > 1:
            self.page = 1
            self.update_buttons()
            await self.update_embed(interaction)

    async def previous(self, interaction):
        if self.page > 1:
            self.page -= 1
            self.update_buttons()
            await self.update_embed(interaction)

    async def next(self, interaction):
        if self.page < self.pages:
            self.page += 1
            self.update_buttons()
            await self.update_embed(interaction)

    async def last(self, interaction):
        if self.page < self.pages:
            self.page = self.pages
            self.update_buttons()
            await self.update_embed(interaction)

    async def send(self):
        self.message = await self.ctx.send(embed=self.embeds[self.page - 1], view=self, content=self.era_string)

    async def update_embed(self, interaction):
        if self.ctx.author.id == interaction.user.id:
            await interaction.response.edit_message(embed=self.embeds[self.page - 1], view=self)

    async def on_timeout(self):
        await self.message.edit(view=None)


def get_descriptions(data_list, formatter, pages=10, per_page=10):
    return ["".join([formatter(data) for data in data_list[i * per_page:(i + 1) * per_page]]) for i in range(pages)]


def update_footer(embed, text):
    footer_text = f"{embed.footer.text}\n" if embed.footer.text else ""
    embed.set_footer(text=footer_text + text)


# Deprecated
def add_profile(embed, stats, universe="play", pfp=True):
    # def add_profile(embed, stats, show_pfp=True):
    username = stats["username"]
    author_icon = (
        f"{web_server}/images/flags/{stats['country'].upper()}.png"
        if stats["country"]
        else f"{web_server}/images/silhouette.png"
    )

    if pfp:
        embed.set_thumbnail(url=urls.profile_picture(username))

    embed.set_author(
        name=username,
        url=urls.profile(username),
        icon_url=author_icon,
    )


# Deprecated
def add_universe(embed, universe):
    if universe == "play":
        return

    if embed.author.url:
        embed.set_author(
            name=embed.author.name,
            url=f"{embed.author.url}&universe={universe}",
            icon_url=embed.author.icon_url,
        )

    footer_text = f"{embed.footer.text}\n" if embed.footer.text else ""
    embed.set_footer(text=footer_text + f"Universe: {universe}")


def is_embed(result):
    return isinstance(result, Embed)
