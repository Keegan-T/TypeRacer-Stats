import asyncio
import random

import aiohttp


def get_random_user_agent():
    if random.randint(0, 3) <= 2:
        version = random.choice(["6.1", "6.2", "6.3", "10.0"])
        os = f"Windows {version}; Win64; x64"
    else:
        sub_version = random.randint(10, 18) % 16
        separator = "_" if random.randint(0, 9) <= 2 else "."
        version = ("10" if sub_version > 3 else "11") + f"{separator}{sub_version}"
        os = f"Macintosh; Intel Mac OS X {version}"

    if random.randint(0, 10) <= 4:
        browser_version = f"{random.randint(42, 86)}.0"
        os +=  f"; rv:{browser_version}"
        user_agent = f"Gecko/20100101 Firefox/{browser_version}"
    else:
        browser_version = f"{random.randint(60, 89)}.0.{random.randint(3000, 4389)}"
        user_agent = f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{browser_version} Safari/537.36"

    return f"Mozilla/5.0 ({os}) {user_agent}"


async def fetch_html(session, url):
    user_agent = get_random_user_agent()
    headers = {"User-agent": user_agent}
    async with session.get(url, headers=headers) as response:
        res = await response.text()
        return res


async def fetch_htmls(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_html(session, url) for url in urls]
        return await asyncio.gather(*tasks)


async def fetch(urls):
    answer = await fetch_htmls(urls)
    return answer
