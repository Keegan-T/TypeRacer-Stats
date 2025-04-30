import os

from discord import Embed, ButtonStyle, File
from discord.ui import View, Button

from config import web_server
from utils import urls, strings


class Page:
    def __init__(self, title=None, description=""):
        self.title = title
        self.description = description


class GraphPage(Page):
    def __init__(self, render, file_name, title=None, description="", button_name=None, default=False):
        super().__init__(title, description)
        self.render = render
        self.file_name = file_name
        self.button_name = button_name
        self.default = default


class MessageView(View):
    def __init__(self, ctx, user, pages, title=None, url=None, header="", color=None, profile=None, universe=None, show_pfp=True):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.message = None
        self.user = user
        self.era_string = strings.get_era_string(user)

        self.title = title
        self.url = url
        self.pages = pages if isinstance(pages, list) else [pages]
        self.header = header
        self.color = color if color else user["colors"]["embed"]
        self.profile = profile
        self.universe = universe
        self.show_pfp = show_pfp
        self.embeds = []

    def add_profile(self, embed):
        username = self.profile["username"]
        author_icon = (
            f"{web_server}/images/flags/{self.profile['country'].upper()}.png"
            if self.profile["country"]
            else f"{web_server}/images/silhouette.png"
        )

        if self.show_pfp:
            embed.set_thumbnail(url=urls.profile_picture(username))

        embed.set_author(
            name=username,
            url=urls.profile(username),
            icon_url=author_icon,
        )

    def add_universe(self, embed):
        if self.universe == "play":
            return

        if embed.author.url:
            embed.set_author(
                name=embed.author.name,
                url=f"{embed.author.url}&universe={self.universe}",
                icon_url=embed.author.icon_url,
            )

        self.update_footer(embed, f"Universe: {self.universe}")

    def update_footer(self, embed, text):
        footer_text = f"{embed.footer.text}\n" if embed.footer.text else ""
        embed.set_footer(text=footer_text + text)

    async def on_timeout(self):
        await super().on_timeout()
        if len(self.pages) > 1:
            await self.message.edit(view=None)


class Message(MessageView):
    def __init__(self, ctx, user, pages, title=None, url=None, header="", color=None, profile=None, universe=None, show_pfp=True):
        super().__init__(ctx, user, pages, title, url, header, color, profile, universe, show_pfp)
        self.page_count = len(self.pages)

        for i, page in enumerate(self.pages):
            title = page.title if page.title else self.title
            description = self.header + page.description
            embed = Embed(
                title=title,
                description=description,
                url=self.url,
                color=self.color,
            )
            if self.profile:
                self.add_profile(embed)
            if self.universe:
                self.add_universe(embed)
            if self.page_count > 1:
                self.update_footer(embed, f"Page {i + 1} of {self.page_count}")
            self.embeds.append(embed)

        self.page = 1
        if self.page_count > 1:
            self.add_navigation_buttons()
            self.update_buttons()

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
        if self.page < self.page_count:
            self.page += 1
            self.update_buttons()
            await self.update_embed(interaction)

    async def last(self, interaction):
        if self.page < self.page_count:
            self.page = self.page_count
            self.update_buttons()
            await self.update_embed(interaction)

    async def send(self):
        self.message = await self.ctx.send(embed=self.embeds[self.page - 1], view=self, content=self.era_string)

    async def update_embed(self, interaction):
        if self.ctx.author.id == interaction.user.id:
            await interaction.response.edit_message(embed=self.embeds[self.page - 1], view=self)


class GraphMessage(MessageView):
    def __init__(self, ctx, user, pages, title=None, url=None, header="", color=None, profile=None, universe=None, show_pfp=True):
        super().__init__(ctx, user, pages, title, url, header, color, profile, universe, show_pfp)
        self.cache = {}
        self.graph_index = 0

        self.embeds = []
        for i, page in enumerate(self.pages):
            if page.default:
                self.graph_index = i
            title = page.title if page.title else self.title
            description = self.header + page.description
            embed = Embed(
                title=title,
                description=description,
                url=self.url,
                color=self.color,
            )
            if self.profile:
                self.add_profile(embed)
            if self.universe:
                self.add_universe(embed)
            self.embeds.append(embed)

        self.update_image()
        if len(self.pages) > 1:
            self.add_graph_buttons()

    def update_image(self):
        index = self.graph_index
        if index not in self.cache:
            page = self.pages[index]
            file_name = page.file_name
            page.render(file_name)
            self.cache[index] = file_name

        self.embeds[index].set_image(url=f"attachment://{self.cache[index]}")

    def add_graph_buttons(self):
        for i, page in enumerate(self.pages):
            style = ButtonStyle.primary if i == self.graph_index else ButtonStyle.secondary
            button = Button(label=page.button_name, style=style)
            button.callback = self.make_callback(i)
            self.add_item(button)

    def make_callback(self, index):
        async def callback(interaction):
            if index == self.graph_index:
                return await interaction.response.defer()

            self.graph_index = index
            self.update_image()

            self.clear_items()
            self.add_graph_buttons()

            await self.update_embed(interaction)

        return callback

    async def send(self):
        file_name = self.cache[self.graph_index]
        file = File(file_name, filename=os.path.basename(file_name))
        self.message = await self.ctx.send(
            embed=self.embeds[self.graph_index],
            view=self,
            content=self.era_string,
            files=[file]
        )

    async def update_embed(self, interaction):
        if self.ctx.author.id != interaction.user.id:
            return await interaction.response.defer()

        file_name = self.cache[self.graph_index]
        file = File(file_name, filename=os.path.basename(file_name))
        await interaction.response.edit_message(
            embed=self.embeds[self.graph_index],
            view=self,
            attachments=[file]
        )

    async def on_timeout(self):
        await super().on_timeout()
        for file in self.cache.values():
            try:
                os.remove(file)
            except (FileNotFoundError, PermissionError):
                return


def get_pages(data_list, formatter, page_count=10, per_page=10):
    page_count = min(page_count, len(data_list) // per_page + 1)
    pages = []
    for i in range(page_count):
        description = ""
        for data in data_list[i * per_page:(i + 1) * per_page]:
            description += formatter(data)
        pages.append(Page(description=description))

    return pages


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
