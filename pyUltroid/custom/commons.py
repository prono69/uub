# some common helper functions exist here..

__all__ = ("not_so_fast", "split_list", "async_lock")

import asyncio


async_lock = asyncio.Lock()


# to use in pmlogger, botpmlogger, etc.
async def not_so_fast(func, *args, sleep=3, **kwargs):
    try:
        await async_lock.acquire()
        return await func(*args, **kwargs)
    finally:
        await asyncio.sleep(sleep)
        async_lock.release()


# from fns.misc
def split_list(List, index):
    new_ = []
    while List:
        new_.extend([List[:index]])
        List = List[index:]
    return new_
