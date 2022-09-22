import asyncio
from random import randrange


class PMLogger:
    def __init__(self, func):
        self.count = 0
        self.DB = {}
        self.active = False
        self.func = func

    async def add(self, msg):
        self.count += 1
        self.DB[self.count] = msg
        if not self.active:
            await self.run()

    def pop(self, key):
        if not key:
            try:
                key = next(iter(self.DB))
            except StopIteration:
                return
        self.DB.pop(key, None)

    def __str__(self):
        count = self.count
        active = self.active
        return (
            f"Total Queued Items - {len(self.DB)} | Active - {active} | Count - {count}"
        )

    async def run(self):
        if not (DB := self.DB):
            self.active = False
            return
        self.active = True
        key = next(iter(DB))
        await self.func(DB.get(key))
        self.pop(key)
        await self.run()
