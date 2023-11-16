# some common helper functions exist here..

__all__ = ("not_so_fast", "split_list", "alock")

import asyncio


alock = asyncio.Lock()


# to use in pmlogger, botpmlogger, etc.
async def not_so_fast(func, *args, sleep=3, **kwargs):
    try:
        await alock.acquire()
        return await func(*args, **kwargs)
    finally:
        await asyncio.sleep(sleep)
        alock.release()


# fns.misc
def split_list(List, index):
    new_ = []
    while List:
        new_.extend([List[:index]])
        List = List[index:]
    return new_
