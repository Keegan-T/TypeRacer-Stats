import asyncio


class LargeQueryLock:
    lock = asyncio.Lock()

    def __init__(self, should_lock: bool):
        self.should_lock = should_lock
        self.acquired = False

    async def __aenter__(self):
        if self.should_lock:
            if self.lock.locked():
                raise RuntimeError("Large query already in progress")
            await self.lock.acquire()
            self.acquired = True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.lock.release()


leaderboard_lock = asyncio.Lock()
average_lock = asyncio.Lock()
import_lock = asyncio.Lock()
match_lock = asyncio.Lock()
line_lock = asyncio.Lock()
tens_lock = asyncio.Lock()
skip_lock = asyncio.Lock()
