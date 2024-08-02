import asyncio
import json
import random

import aiohttp


def generate_random_user_agent():
    firefox = random.randint(0, 9) <= 2
    OS = 'Windows' if random.randint(0, 3) <= 2 else 'Macintosh; Intel Mac OS X'
    if OS[0] == 'W':
        OS_version = random.choice(['6.1', '6.2', '6.3', '10.0'])
        OS = f"{OS} {OS_version}; Win64; x64"
    else:
        OS_version = random.randint(10, 18) % 16
        if firefox:
            OS_version = f"10.{OS_version}" if OS_version > 3 else f"11.{OS_version}"
        else:
            OS_version = f"10_{OS_version}" if OS_version > 3 else f"11_{OS_version}"
        OS = f"{OS} {OS_version}"

    firefox = random.randint(0, 10) <= 4
    if firefox:
        browser_version = f"{str(random.randint(42, 86))}.0"
        user_agent = f"Mozilla/5.0 ({OS}; rv:{browser_version}) Gecko/20100101 Firefox/{browser_version}"
    else:
        browser_version = f"{random.randint(60, 89)}.0.{random.randint(3000, 4389)}"
        user_agent = f"Mozilla/5.0 ({OS}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{browser_version} Safari/537.36"
    return user_agent


async def fetch_html(session, url, scraper, store_url):
    headers = {'User-agent': generate_random_user_agent()}
    async with session.get(url, headers=headers) as response:
        response_ = await response.text()
        if store_url:
            return {url: scraper(response_)}
        return scraper(response_)


async def fetch_json(session, url, scraper, store_url):
    headers = {'User-agent': generate_random_user_agent()}
    async with session.get(url, headers=headers) as response:
        response_ = json.loads(await response.read())
        if store_url:
            return {url: scraper(response_)}
        return scraper(response_)


async def fetch_htmls(urls, scraper, store_url):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_html(session, url, scraper, store_url) for url in urls]
        return await asyncio.gather(*tasks)


async def fetch(urls, scraper=lambda x: x, store_url=False):
    answer = await fetch_htmls(urls, scraper, store_url)
    return answer
