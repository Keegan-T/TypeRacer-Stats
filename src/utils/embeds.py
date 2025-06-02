import os

from discord import Embed, ButtonStyle, File
from discord.ui import View, Button

from utils import urls, strings, files


class Page:
    def __init__(self, title=None, description="", fields=None, footer=None, color=None,
                 button_name=None, render=None, default=False):
        self.title = title
        self.description = description
        self.fields = fields if isinstance(fields, list) else [fields] if fields else None
        self.footer = footer
        self.color = color
        self.button_name = button_name
        self.default = default
        self.render = render


class Field:
    def __init__(self, name, value, inline=True):
        self.name = name
        self.value = value
        self.inline = inline


class Message(View):
    def __init__(self, ctx, user, pages, title=None, url=None, header="", footer="", content="",
                 color=None, profile=None, universe=None, show_pfp=True, time_travel=True):
        self.pages = pages if isinstance(pages, list) else [pages]
        self.page_count = len(self.pages)
        super().__init__(timeout=60 if self.page_count > 1 else 0.01)

        self.ctx = ctx
        self.message = None
        self.user = user
        if content:
            self.content = content
        elif time_travel:
            self.content = strings.get_era_string(user)
        else:
            self.content = ""
        self.title = title
        self.url = url
        self.index = 0
        self.header = header
        self.footer = footer
        self.color = color if color else user["colors"]["embed"]
        self.profile = profile
        self.universe = universe
        self.show_pfp = show_pfp
        self.embeds = []
        self.cache = {}
        self.paginated = any(not page.button_name for page in self.pages)

        for i, page in enumerate(self.pages):
            title = page.title if page.title else self.title
            description = self.header + page.description
            footer = page.footer if page.footer else self.footer
            if page.default:
                self.index = i
            embed = Embed(
                title=title,
                description=description,
                url=self.url,
                color=page.color if page.color else self.color,
            )
            if page.fields:
                for field in page.fields:
                    embed.add_field(name=field.name, value=field.value, inline=field.inline)
            if footer:
                self.update_footer(embed, footer)
            if self.profile:
                self.add_profile(embed)
            if self.universe:
                self.add_universe(embed)
            if self.paginated and self.page_count > 1:
                self.update_footer(embed, f"Page {i + 1} of {self.page_count}")
            self.embeds.append(embed)

        if self.pages[self.index].render:
            self.update_image()
        if self.page_count > 1:
            if self.paginated:
                self.add_navigation_buttons()
                self.update_navigation_buttons()
            else:
                self.add_buttons()

    def add_profile(self, embed):
        username = self.profile["username"]
        author_icon = (
            f"https://flagsapi.com/{self.profile['country'].upper()}/flat/64.png"
            if self.profile["country"]
            else "https://i.postimg.cc/Dw2jbV3N/silhouette.png"
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

    def update_navigation_buttons(self):
        self.children[0].disabled = self.index == 0
        self.children[1].disabled = self.index == 0
        self.children[2].disabled = self.index == self.page_count - 1
        self.children[3].disabled = self.index == self.page_count - 1

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
        if self.index > 0:
            self.index = 0
            self.update_navigation_buttons()
            await self.update_embed(interaction)

    async def previous(self, interaction):
        if self.index > 0:
            self.index -= 1
            self.update_navigation_buttons()
            await self.update_embed(interaction)

    async def next(self, interaction):
        if self.index < self.page_count - 1:
            self.index += 1
            self.update_navigation_buttons()
            await self.update_embed(interaction)

    async def last(self, interaction):
        if self.index < self.page_count - 1:
            self.index = self.page_count - 1
            self.update_navigation_buttons()
            await self.update_embed(interaction)

    def add_buttons(self):
        for i, page in enumerate(self.pages):
            style = ButtonStyle.primary if i == self.index else ButtonStyle.secondary
            button = Button(label=page.button_name, style=style)
            button.callback = self.make_callback(i)
            self.add_item(button)

    def make_callback(self, index):
        async def callback(interaction):
            if index == self.index:
                return await interaction.response.defer()

            self.index = index
            if self.pages[self.index].render:
                self.update_image()
            self.clear_items()
            self.add_buttons()

            await self.update_embed(interaction)

        return callback

    def update_image(self):
        index = self.index
        if index not in self.cache:
            page = self.pages[index]
            file_name = page.render()
            self.cache[index] = file_name

        self.embeds[index].set_image(url=f"attachment://{self.cache[index]}")

    async def update_embed(self, interaction):
        if self.ctx.author.id != interaction.user.id:
            return await interaction.response.defer()

        kwargs = {
            "embed": self.embeds[self.index],
            "view": self,
        }
        if self.pages[self.index].render:
            file_name = self.cache[self.index]
            file = File(file_name, filename=os.path.basename(file_name))
            kwargs["attachments"] = [file]
        else:
            kwargs["attachments"] = []
        await interaction.response.edit_message(**kwargs)

    async def send(self):
        kwargs = {
            "embed": self.embeds[self.index],
            "view": self,
            "content": self.content,
        }
        if self.pages[self.index].render:
            file_name = self.cache[self.index]
            file = File(file_name, filename=os.path.basename(file_name))
            kwargs["files"] = [file]
        self.message = await self.ctx.send(**kwargs)

    async def on_timeout(self):
        await super().on_timeout()
        if len(self.pages) > 1:
            await self.message.edit(view=None)
        for file in self.cache.values():
            files.remove_file(file)


def get_pages(data_list, formatter, page_count=10, per_page=10):
    page_count = min(page_count, ((len(data_list) - 1) // per_page) + 1)
    pages = []
    for i in range(page_count):
        description = ""
        for data in data_list[i * per_page:(i + 1) * per_page]:
            description += formatter(data)
        pages.append(Page(description=description))

    return pages


# Deprecated
def add_profile(embed, stats, universe="play", pfp=True):
    username = stats["username"]
    author_icon = (
        f"https://flagsapi.com/{stats['country'].upper()}/flat/64.png"
        if stats["country"]
        else "https://i.postimg.cc/Dw2jbV3N/silhouette.png"
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
