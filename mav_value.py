import asyncio
from time import time
from logging import getLogger


class MavValue:
    timeout = 10

    def __init__(self, generator):
        self.generator = generator
        self.val = None
        self.lastUpdate = time()
        self.updater = asyncio.create_task(self.keep_updated())

    async def keep_updated(self):
        async for val in self.generator():
            self.val = val
            now = time()
            if now - self.lastUpdate >= MavValue.timeout:
                # getLogger().warning(f"Timeout on value {val}, delay {now - self.lastUpdate}")
                pass
            self.lastUpdate = now
