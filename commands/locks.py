import asyncio

average_lock = asyncio.Lock()
match_lock = asyncio.Lock()
line_lock = asyncio.Lock()