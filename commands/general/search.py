from discord import Embed
from discord.ext import commands
import urls
import utils
import errors
import colors
import commands.recent as recent
from config import prefix
from database.bot_users import get_user
from database.texts import get_texts
import Levenshtein

command = {
    "name": "search",
    "aliases": ["query", "q", "lf", "searchid", "id"],
    "description": "Searches the text database for matching results\n"
                   "Displays similar results if there are no exact matches\n"
                   f"`{prefix}searchid [text_id]` will search for a text ID",
    "parameters": "[query]",
    "usages": ["search They don't know", "search 3550533"],
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
    query_length = len(query)
    if query_length > 250:
        return await ctx.send(embed=big_query())

    text_list = get_texts()
    query_title = query.replace("`", "")
    query = query.lower()
    search_id = ctx.invoked_with in ["searchid", "id"]
    title = f"Text {'ID ' * search_id}Search"
    results = []

    if search_id:
        text_id_match = next((text for text in text_list if str(text["id"]) == query), None)
        if text_id_match:
            results.append(text_id_match)
        else:
            embed = Embed(
                title=title,
                description=f'No results found.\n**Query:** "{query}"',
                color=user["colors"]["embed"],
            )
            return await ctx.send(embed=embed)

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

    results_string = (
        f'Displaying **{min(result_count, 10)}** of **{result_count:,}** '
        f'result{"s" * (result_count != 1)}.\n**Query:** "{query_title}"\n'
    )

    if no_matches:
        results_string = f'No results found, displaying similar results.\n**Query:** "{query_title}"\n'

    if search_id:
        result = results[0]
        quote = utils.truncate_clean(result["quote"], max_chars)
        results_string += (
            f"\n[#**{result['id']}**]({urls.trdata_text(result['id'])})"
            f"{' (Disabled)' * result['disabled']} - [Ghost]({result['ghost']})\n"
            f'"{quote}"\n'
        )
    else:
        for result in results[:10]:
            quote = result["quote"].strip().replace("*", "\*").replace("_", "\_")
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
            substring += f"**{quote[query_index:query_index + query_length]}**"
            substring += quote[query_index + query_length:end_index]
            if end_index < len(quote):
                substring += "..."

            results_string += (
                f"\n[#{result['id']}](https://typeracerdata.com/text?id={result['id']})"
                f"{' (Disabled) ' * result['disabled']}"
            )

            if no_matches:
                similarity = (1 - (result["leven"]["distance"] / query_length)) * 100
                results_string += f" - {similarity:,.2f}% Match"

            results_string += f' - {len(quote):,} characters - [Ghost]({result["ghost"]})\n"{substring}"\n'

    embed = Embed(
        title=title,
        description=results_string,
        color=user["colors"]["embed"],
    )

    if result_count > 10:
        embed.set_footer(text="Use a more specific query to narrow search results")

    await ctx.send(embed=embed)

    recent.text_id = results[0]["id"]


def big_query():
    return Embed(
        title="Query Too Long",
        description="Query cannot exceed 250 characters",
        color=colors.error,
    )


async def setup(bot):
    await bot.add_cog(Search(bot))
