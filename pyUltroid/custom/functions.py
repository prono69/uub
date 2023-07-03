import asyncio
from ast import literal_eval
from functools import wraps
from pathlib import Path
from random import choice, randrange
from shlex import split as shsplit
import string
from time import perf_counter

from telethon.tl import types
from telethon.tl.functions.messages import SaveGifRequest
from telethon.utils import get_display_name, get_input_document
from telethon.tl.types import InputMessagesFilterPhotos

from ._loop import loop, run_async_task
from pyUltroid.startup import LOGS, HOSTED_ON
from pyUltroid.fns.helper import async_searcher, osremove, asyncread, asyncwrite
from pyUltroid.fns.misc import random_string
from pyUltroid import asst, udB, ultroid_bot


# scheduler
def init_scheduler():
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ImportError:
        return None

    schd = AsyncIOScheduler(timezone="Asia/Kolkata")
    schd.start()
    return schd


scheduler = init_scheduler()


# https://gist.github.com/DougAF/ef88f89d1d99763bb05afd81285ef233#file-timer-py
def timeit(func):
    """To Check running time of functions."""

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def exec_time(*args, **kwargs):
            start = perf_counter()
            result = await func(*args, **kwargs)
            time_taken = perf_counter() - start
            return f"Function: {func.__name__} \nOutput: {result} \nTime taken: {time_taken:.5f} seconds."

        return exec_time
    else:

        @wraps(func)
        def exec_time(*args, **kwargs):
            start = perf_counter()
            result = func(*args, **kwargs)
            time_taken = perf_counter() - start
            return f"Function: {func.__name__} \nOutput: {result} \nTime taken: {time_taken:.5f} seconds."

        return exec_time


async def cleargif(gif):
    if not gif.client._bot and gif.gif:
        try:
            await gif.client(SaveGifRequest(id=get_input_document(gif), unsave=True))
        except Exception as ex:
            return LOGS.warning(f"error in cleargif: {ex}", exc_info=True)


async def get_imgbb_link(path, **kwargs):
    api = udB.get_key("IMGBB_API")
    if not (api and Path(path).is_file()):
        return
    image_data = await asyncread(path, binary=True)
    if kwargs.get("delete"):
        osremove(path)
    post = await async_searcher(
        "https://api.imgbb.com/1/upload",
        post=True,
        data={
            "key": api,
            "image": image_data,
            "name": kwargs.get("title", random_string(length=9)),
            "expiration": str(kwargs.get("expire", 0)),
        },
        re_json=True,
    )
    if post.get("status") == 200:
        flink = post["data"]["url"] if kwargs.get("hq") else post["data"]["display_url"]
        if "preview" in kwargs:
            try:
                await asst.send_message(
                    udB.get_key("TAG_LOG"), flink, link_preview=True
                )
                await asyncio.sleep(3)
            except Exception as exc:
                LOGS.warning("ImgBB preview error:", exc_info=True)
        return flink
    else:
        from pyUltroid.fns.tools import json_parser

        return LOGS.error(json_parser(post, indent=4))


class RandomPhotoHandler:
    def __init__(self):
        self.ok = bool(udB.get_key("__RANDOM_PIC", force=True))
        self.running = False
        self.photos_to_store = 20
        self.sources = (
            ("r_wallpapers", 9547, 29000),
            ("Anime_hot_wallpapers", 5, 11500),
        )

    async def get(self, clear=True):
        photos = udB.get_key("__RANDOM_PIC", force=True) or []
        if not photos:
            run_async_task(self._save_images, id="random_pic")
            return None
        pic = choice(photos)
        if clear:
            photos.remove(pic)
            udB.set_key("__RANDOM_PIC", photos)
            if not self.running:
                run_async_task(self._save_images, id="random_pic")
        return pic

    async def _save_images(self):
        self.running = True
        pics = udB.get_key("__RANDOM_PIC", force=True)
        if len(pics) >= self.photos_to_store:
            return

        for _ in range(self.photos_to_store - len(pics)):
            chat, min_id, max_id = choice(self.sources)
            async for msg in ultroid_bot.iter_messages(
                chat,
                limit=1,
                filter=InputMessagesFilterPhotos,
                offset_id=randrange(min_id, max_id),
            ):
                pic_name = chat + "_" + str(msg.id)
                await asyncio.sleep(randrange(10, 35))
                path = await msg.download_media()
                imgbb_link = await get_imgbb_link(
                    path,
                    expire=10 * 86400,
                    title=pic_name,
                    delete=True,
                    preview=True,
                )
                pics.append(imgbb_link)
        udB.set_key("__RANDOM_PIC", pics)
        self.running = False


random_pic = RandomPhotoHandler()


class unix_parser:
    def __init__(self, text):
        self.args = []
        self.kwargs = {}
        split = shsplit(text)
        for word in split:
            if word.startswith("-") and len(word) > 1:
                split = word.split("=", maxsplit=1)
                key, value = split if len(split) > 1 else (word, "True")
                self.kwargs[key[1:]] = self._checker(value)
            else:
                self.args.append(word)

        self.args = " ".join(self.args)

    @staticmethod
    def _checker(data):
        try:
            return literal_eval(data)
        except Exception:
            return data


__all__ = [
    "timeit",
    "cleargif",
    "osremove",
    "get_imgbb_link",
    "random_pic",
    "run_async_task",
    "scheduler",
    "unix_parser",
]
