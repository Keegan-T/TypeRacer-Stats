from discord import Embed
from discord.ext import commands
import utils
import errors
import colors
import commands.recent as recents
from config import prefix
from database.bot_users import get_user
from database.texts import get_texts
import Levenshtein

info = {
    "name": "search",
    "aliases": ["query", "q", "lf"],
    "description": "Searches the text database for matching results\n"
                   "Displays similar results if there are no exact matches\n"
                   f"`{prefix}search [text_id]` will search for a text ID",
    "parameters": "[query]",
    "usages": ["search They don't know"],
    "import": False,
}


class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info['aliases'])
    async def search(self, ctx, *, query=None):
        user = get_user(ctx)
        if not query:
            return await ctx.send(embed=errors.missing_param(info))

        await run(ctx, user, query)


async def run(ctx, user, query):
    text_list = get_texts()
    query_title = query.replace("`", "")
    query = query.lower()
    query_length = len(query)
    results = []

    search_id = next((text for text in text_list if str(text["id"]) == query), None)

    for text in text_list:
        if query in text["quote"].lower():
            results.append(text)

    if query_length > 250:
        return await ctx.send(embed=big_query())

    result_count = len(results)
    show_similar = result_count == 0

    max_chars = 150

    if show_similar:
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

    results_string = (
        f'Displaying **{min(result_count, 10)}** of **{result_count:,}** '
        f'result{"s" * (result_count != 1)}.\n**Query:** "{query_title}"\n'
    )

    if show_similar:
        results_string = f'No results found, displaying similar results.\n**Query:** "{query_title}"\n'

    if search_id:
        results.insert(0, search_id)

    for result in results[:10]:
        if result == search_id:
            quote = utils.truncate_clean(result["quote"], max_chars)
            results_string += (
                f"\n[#**{result['id']}**](https://typeracerdata.com/text?id={result['id']}) - ID Match"
                f"{' (Disabled)' * result['disabled']} - [Ghost]({result['ghost']})\n"
                f'"{quote}"\n'
            )

        else:
            quote = result["quote"].strip().replace("*", "\*").replace("_", "\_")
            chars = max_chars - query_length
            if show_similar:
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
            substring += f"**{quote[query_index:query_index + query_length]}**"
            substring += quote[query_index + query_length:end_index]
            if end_index < len(quote):
                substring += "..."

            results_string += (
                f"\n[#{result['id']}](https://typeracerdata.com/text?id={result['id']})"
                f"{' (Disabled) ' * result['disabled']}"
            )

            if show_similar:
                similarity = (1 - (result["leven"]["distance"] / query_length)) * 100
                results_string += f" - {similarity:,.2f}% Match"

            results_string += f' - [Ghost]({result["ghost"]})\n"{substring}"\n'

    embed = Embed(
        title=f"Text Search",
        description=results_string,
        color=user["colors"]["embed"],
    )

    if result_count > 10:
        embed.set_footer(text="Use a more specific query to narrow search results")

    await ctx.send(embed=embed)

    recents.text_id = results[0]["id"]


def big_query():
    return Embed(
        title="Query Too Long",
        description="Query cannot exceed 250 characters",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Search(bot))
