import Levenshtein
from discord import Embed
from discord.ext import commands

import database.bot.recent_text_ids as recent
from config import prefix
from database.bot.users import get_user
from database.main.texts import get_texts
from utils import errors, colors, urls, strings
from utils.embeds import Page, Message, get_pages

command = {
    "name": "search",
    "aliases": ["query", "q", "lf", "searchid", "id"],
    "description": "Searches the text database for matching results\n"
                   "Displays similar results if there are no exact matches\n"
                   f"`{prefix}searchid [text_id]` will search for a text ID",
    "parameters": "[query]",
    "usages": ["search They don't know", "searchid 3550533"],
}


class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def search(self, ctx, *, query=None):
        user = get_user(ctx)
        if not query:
            return await ctx.send(embed=errors.missing_argument(command))

        await run(ctx, user, query)


async def run(ctx, user, query):
    universe = user["universe"]
    query_length = len(query)
    if query_length > 250:
        return await ctx.send(embed=big_query())

    text_list = get_texts(universe=universe)
    query_title = strings.escape_formatting(query)
    query = query.lower()
    search_id = ctx.invoked_with in ["searchid", "id"]
    title = f"Text {'ID ' * search_id}Search"
    results = []

    if search_id:
        text_id_match = next((text for text in text_list if str(text["text_id"]) == query), None)
        if text_id_match:
            results.append(text_id_match)
        else:
            message = Message(
                ctx, user, Page(
                    title=title,
                    description=f'No results found.\n**Query:** "{query_title}"',
                )
            )

            return await message.send()

    else:
        for text in text_list:
            if query in text["quote"].lower():
                results.append(text)

    result_count = len(results)
    no_matches = result_count == 0
    max_chars = 150

    if no_matches:
        for text in text_list:
            quote = text["quote"].lower()
            min_leven = {"distance": float("inf"), "start": 0, "end": 0}
            start_index = 0
            end_index = min(len(query), len(quote) - 1)
            while end_index < len(quote):
                substring = quote[start_index:end_index]
                leven = Levenshtein.distance(query, substring)
                if leven < min_leven["distance"]:
                    min_leven = {
                        "distance": leven,
                        "start": start_index,
                        "end": end_index
                    }
                start_index += 1
                end_index += 1
            text["leven"] = min_leven

        results = sorted(text_list, key=lambda t: t["leven"]["distance"])

    header = (
        f'Displaying **{min(result_count, 10)}** of **{result_count:,}** '
        f'result{"s" * (result_count != 1)}.\n**Query:** "{query_title}"\n'
    )

    if no_matches:
        header = f'No results found, displaying similar results.\n**Query:** "{query_title}"\n'

    if search_id:
        result = results[0]
        quote = strings.truncate_clean(result["quote"], max_chars)
        pages = Page(
            description=(
                f"\n[#**{result['text_id']}**]({urls.trdata_text(result['text_id'], universe)})"
                f"{' (Disabled)' * result['disabled']} - [Ghost]({result['ghost']})\n"
                f'"{quote}"\n'
            )
        )

    else:
        def formatter(result):
            description = ""
            quote = result["quote"]
            chars = max_chars - query_length
            if no_matches:
                start_index = result["leven"]["start"]
                end_index = result["leven"]["end"]
                query_index = start_index
            else:
                query_index = quote.lower().find(query)
                start_index = query_index
                end_index = query_index + query_length

            while chars > 0 and end_index - start_index < len(quote):
                if start_index > 0:
                    start_index -= 1
                    chars -= 1
                if end_index < len(quote):
                    end_index += 1
                    chars -= 1

            while start_index > 0 and quote[start_index] != " ":
                start_index -= 1

            if start_index > 0:
                start_index += 1

            while end_index < len(quote) and quote[end_index].isalnum():
                end_index += 1

            substring = ""
            if start_index > 0:
                substring += "..."
            substring += quote[start_index:query_index]
            substring += f"\t{quote[query_index:query_index + query_length]}\t"
            substring += quote[query_index + query_length:end_index]
            if end_index < len(quote):
                substring += "..."

            description += (
                f"\n[#{result['text_id']}]({urls.trdata_text(result['text_id'], universe)})"
                f"{' (Disabled) ' * result['disabled']}"
            )

            if no_matches:
                similarity = 1 - (result["leven"]["distance"] / query_length)
                description += f" - {similarity:.2%} Match"

            description += (
                f' - {len(quote):,} characters - [Ghost]({result["ghost"]})\n'
                f'"{strings.escape_formatting(substring).replace('\t', '**')}"\n'
            )

            return description

        pages = get_pages(results, formatter, page_count=10, per_page=5)

    message = Message(
        ctx, user, pages,
        title=title,
        header=header,
        footer="Use a more specific query to narrow search results" * (result_count > 50),
        universe=universe
    )

    await message.send()

    recent.update_recent(ctx.channel.id, results[0]["text_id"])


def big_query():
    return Embed(
        title="Query Too Long",
        description="Query cannot exceed 250 characters",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Search(bot))
