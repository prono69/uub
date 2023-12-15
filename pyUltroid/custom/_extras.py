# additional functions that must be seperate from commons..

__all__ = ("aiohttp_client", "cpu_bound", "run_async", "async_searcher")

import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial, wraps

from pyUltroid.exceptions import DependencyMissingError
from ._loop import loop

try:
    import requests
except ImportError:
    requests = None

try:
    from aiohttp import ClientSession as aiohttp_client
except ImportError:
    aiohttp_client = None


_workers = __import__("multiprocessing").cpu_count()


# source: fns/helper.py
# preferred for I/O bound task.
def run_async(function):
    @wraps(function)
    async def wrapper(*args, **kwargs):
        return await loop.run_in_executor(
            ThreadPoolExecutor(max_workers=_workers * 2),
            partial(function, *args, **kwargs),
        )

    return wrapper


# preferred for cpu bound tasks.
def cpu_bound(function):
    @wraps(function)
    async def wrapper(*args, **kwargs):
        with ProcessPoolExecutor(max_workers=_workers) as pool:
            output = await loop.run_in_executor(
                pool,
                partial(function, *args, **kwargs),
            )
        return output

    return wrapper


# source: fns/helper.py
# Async Searcher -> @buddhhu
async def async_searcher(
    url: str,
    post: bool = False,
    method: str = "GET",
    headers: dict = None,
    evaluate: callable = None,
    object: bool = False,
    re_json: bool = False,
    re_content: bool = False,
    *args,
    **kwargs,
):
    method = "POST" if post else method.upper()
    if aiohttp_client:
        async with aiohttp_client(headers=headers) as client:
            data = await client.request(method, url, *args, **kwargs)
            if evaluate:
                from telethon.helpers import _maybe_await

                return await _maybe_await(evaluate(data))
            elif re_json:
                return await data.json()
            elif re_content:
                return await data.read()
            elif object:
                return data
            else:
                return await data.text()
    elif requests:

        @run_async
        def sync_request():
            data = requests.request(
                method,
                url,
                *args,
                headers=headers,
                **kwargs,
            )
            if object:
                return data
            elif re_json:
                return data.json()
            elif re_content:
                return data.content
            else:
                return data.text

        if evaluate:
            object = True
        data = await sync_request()
        if evaluate:
            from telethon.helpers import _maybe_await

            return await _maybe_await(evaluate(data))
        return data
    else:
        raise DependencyMissingError("Install 'aiohttp' to use this.")
