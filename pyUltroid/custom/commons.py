# some common helper functions exist here..

__all__ = ("not_so_fast",)

import asyncio


async_lock = asyncio.Lock()


# to use in pmlogger, botpmlogger etc.
async def not_so_fast(func, *args, sleep=3, **kwargs):
    try:
        await async_lock.acquire()
        await func(*args, **kwargs)
    finally:
        await asyncio.sleep(sleep)
        await async_lock.release()
