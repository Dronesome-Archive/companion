import asyncio
from time import time

import log


class MavValue:
    TIMEOUT = 10

    def __init__(self, generator):
        self.generator = generator
        self.val = None
        self.lastUpdate = time()
        self.updater = asyncio.create_task(self.keep_updated())

    async def keep_updated(self):
        async for val in self.generator():
            self.val = val
            now = time()
            if now - self.lastUpdate >= MavValue.TIMEOUT:
                log.warn('value came too late', now-self.lastUpdate, 'seconds delay')
            self.lastUpdate = now
