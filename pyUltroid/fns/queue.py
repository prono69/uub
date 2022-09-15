import time
import asyncio

from .. import asst, LOGS


class forwarderQueue:
    def __init__(self, func):
        self.count = 0
        self.DB = {}
        self.running = []  # to cancel
        self.isWorking = False
        self.func = func

    def add(self, callback=True, **args):
        if not args:
            return
        self.count += 1
        self.DB[self.count] = args
        if not self.isWorking and callback:
            self.run()

    def pop(self, key):
        self.DB.pop(key, None)

    def __str__(self):
        count = self.count
        active = self.isWorking
        return f"Total Items - {len(self.DB)} | Active - {active} | Count - {count}"

    @property
    def current(self):
        if self.running:
            return self.running[0]

    async def solo(self, args):
        task = asst.loop.create_task(self.func(**args))
        self.running.append(task)
        await task

    def cleanup(self, key):
        self.pop(key)
        self.running.clear()

    def run(self):
        if not (DB := self.DB):
            self.isWorking = False
            return
        self.isWorking = True
        key = next(iter(DB))
        asyncio.run(self.solo(DB.get(key)))
        self.cleanup(key)
        self.run()
