# some common helper functions exist here..

import asyncio
import os
import json
import random
import re
import string
import time
from datetime import datetime
from mimetypes import guess_extension
from pathlib import Path
from secrets import choice, token_hex
from shutil import rmtree, which
from urllib.parse import urlsplit, urlparse, unquote_plus

from telethon.tl import types
from telethon.errors import MessageNotModifiedError

from pyUltroid.startup import LOGS
from ._extras import *

try:
    import aiofiles
except ImportError:
    aiofiles = None


# ---------------------------------------------------------------- #


if not aiohttp_client:
    LOGS.warning("'aiohttp' is missing, some plugins will not work.")

async_lock = asyncio.Lock()
_PROGRESS_LOG = {}


# used in pmlogger, taglog, botpmlogger, etc.
async def not_so_fast(func, *args, sleep=3, **kwargs):
    try:
        await async_lock.acquire()
        return await func(*args, **kwargs)
    finally:
        await asyncio.sleep(sleep)
        async_lock.release()


# ---------------------- custom ------------------------------------------ #


def check_filename(filroid):
    filroid = Path(filroid)
    num = 1
    while filroid.exists():
        og_stem = filroid.stem
        if suffix := re.search(r"(?:.+)_(\d+)$", og_stem):
            og_stem = og_stem.rsplit("_", maxsplit=1)[0]
            num = int(suffix.group(1)) + 1
        filroid = filroid.with_stem(f"{og_stem}_{num}")
        num += 1
    else:
        return str(filroid)


def osremove(*files, folders=False):
    for path in files:
        try:
            Path(path).unlink(missing_ok=True)
        except IsADirectoryError:
            if folders:
                rmtree(path, ignore_errors=True)
        except Exception:
            LOGS.exception(f"Error in deleting: {path}")


class _TGFilename:
    __slots__ = ("tg_media",)

    def __init__(self, tg_media):
        if isinstance(tg_media, types.Message):
            if not tg_media.media:
                raise ValueError("Not a media File.")
            self.tg_media = tg_media.media
        else:
            self.tg_media = tg_media

    @classmethod
    def init(cls, tg_media):
        self = cls(tg_media)
        return self.get_filename()

    def generate_filename(self, media_type, ext=None):
        date = datetime.now()
        filename = "{}_{}-{:02}-{:02}_{:02}-{:02}-{:02}".format(
            media_type,
            date.year,
            date.month,
            date.day,
            date.hour,
            date.minute,
            date.second,
        )
        return filename + ext if ext else filename

    def get_filename(self):
        if isinstance(self.tg_media, (types.MessageMediaDocument, types.Document)):
            doc = (
                self.tg_media
                if isinstance(self.tg_media, types.Document)
                else self.tg_media.document
            )
            for attr in doc.attributes:
                if isinstance(attr, types.DocumentAttributeFilename):
                    return attr.file_name
            mime = doc.mime_type
            return self.generate_filename(
                mime.split("/", 1)[0], ext=guess_extension(mime)
            )
        elif isinstance(self.tg_media, types.MessageMediaPhoto):
            return self.generate_filename("photo", ext=".jpg")
        else:
            raise ValueError("Invalid media File.")


get_tg_filename = _TGFilename.init


def get_filename_from_url(url):
    if not (path := urlsplit(url).path):
        return token_hex(nbytes=8)
    filename = unquote_plus(Path(path).name)
    if len(filename) > 62:
        filename = str(Path(filename).with_stem(filename[:60]))
    return filename


def string_is_url(url):
    result = urlparse(url)
    return bool(result.scheme and result.netloc)


# asyncread
if aiofiles:

    async def asyncread(file, binary=False):
        read_type = "rb" if binary else "r+"
        async with aiofiles.open(file, read_type) as f:
            data = await f.read()
        return data
else:

    @run_async
    def asyncread(file, binary=False):
        read_type = "rb" if binary else "r+"
        with open(file, read_type) as f:
            data = f.read()
        return data


# asyncwrite
if aiofiles:

    async def asyncwrite(file, data, mode):
        async with aiofiles.open(file, mode) as f:
            await f.write(data)
        return True
else:

    @run_async
    def asyncwrite(file, data, mode):
        with open(file, mode) as f:
            f.write(data)
        return True


# ---------------------- extras ------------------------------------------ #


# source: fns/helper.py
async def bash(cmd, shell=which("bash")):
    """run any command in subprocess and get output or error"""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        executable=shell,
    )
    stdout, stderr = await process.communicate()
    err = stderr.decode(errors="replace").strip() or None
    out = stdout.decode(errors="replace").strip()
    return out, err


# source: fns/helper.py
def time_formatter(milliseconds):
    minutes, seconds = divmod(int(milliseconds / 1000), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    tmp = (
        ((str(weeks) + "w:") if weeks else "")
        + ((str(days) + "d:") if days else "")
        + ((str(hours) + "h:") if hours else "")
        + ((str(minutes) + "m:") if minutes else "")
        + ((str(seconds) + "s") if seconds else "")
    )
    if not tmp:
        return "0s"

    if tmp.endswith(":"):
        return tmp[:-1]
    return tmp


# source: fns/helper.py
def humanbytes(size):
    if not size:
        return "0 B"
    for unit in ("", "K", "M", "G", "T"):
        if size < 1024:
            break
        size /= 1024
    if isinstance(size, int):
        size = f"{size}{unit}B"
    elif isinstance(size, float):
        size = f"{size:.2f}{unit}B"
    return size


# source: fns/tools.py
def split_list(List, index):
    new_ = []
    while List:
        new_.extend([List[:index]])
        List = List[index:]
    return new_


# source: fns/misc.py
def get_all_files(path, extension=None):
    filelist = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if not (extension and not file.endswith(extension)):
                filelist.append(os.path.join(root, file))
    return sorted(filelist)


# source: fns/tools.py
def json_parser(data, indent=None, ascii=False):
    parsed = {}
    try:
        if isinstance(data, str):
            parsed = json.loads(str(data))
            if indent:
                parsed = json.dumps(
                    json.loads(str(data)),
                    indent=indent,
                    ensure_ascii=ascii,
                )
        elif isinstance(data, dict):
            parsed = data
            if indent:
                parsed = json.dumps(data, indent=indent, ensure_ascii=ascii)
    except json.decoder.JSONDecodeError:
        parsed = eval(data)
    return parsed


# source: fns/misc.py
def random_string(length=12, numbers=False, symbols=False):
    """Generate random string of 'n' Length"""
    # return "".join(random.choices(string.ascii_uppercase, k=length))
    _all = list(string.ascii_letters)
    if numbers:
        _all.extend(list(string.digits))
    if symbols:
        _all.extend(list(string.punctuation))
    for _ in range(length // 3):
        random.shuffle(_all)
    rnd_str = "".join(choice(_all) for _ in range(length + 12))
    return "".join(random.sample(rnd_str, length))


# setattr(random, "random_string", random_string)


async def progress(current, total, event, start, type_of_ps, file_name=None):
    jost = str(event.chat_id) + "_" + str(event.id)
    plog = _PROGRESS_LOG.get(jost)
    now = time.time()
    if plog and current != total:
        if (now - plog) < 8:  # delay of 8s b/w each edit
            return
    diff = now - start
    percentage = current * 100 / total
    speed = current / diff
    time_to_completion = round((total - current) / speed) * 1000
    bar_count = min(int(percentage // 5), 20)
    progress_str = "`[{0}{1}] {2}%`\n\n".format(
        "●" * bar_count,
        "" * (20 - bar_count),
        round(percentage, 2),
    )
    tmp = progress_str + "`{0} of {1}`\n\n`✦ Speed: {2}/s`\n\n`✦ ETA: {3}`\n\n".format(
        humanbytes(current),
        humanbytes(total),
        humanbytes(speed),
        time_formatter(time_to_completion),
    )
    to_edit = (
        "`✦ {}`\n\n`File Name: {}`\n\n{}".format(type_of_ps, file_name, tmp)
        if file_name
        else "`✦ {}`\n\n{}".format(type_of_ps, tmp)
    )
    try:
        _PROGRESS_LOG.update({jost: now})
        await event.edit(to_edit)
    except MessageNotModifiedError as exc:
        LOGS.warning("err in progress: message_not_modified")


__all__ = (
    "run_async",
    "check_filename",
    "cpu_bound",
    "osremove",
    "get_tg_filename",
    "get_filename_from_url",
    "string_is_url",
    "asyncread",
    "asyncwrite",
    "bash",
    "async_searcher",
    "time_formatter",
    "humanbytes",
    "not_so_fast",
    "split_list",
    "get_all_files",
    "json_parser",
    "random_string",
    "progress",
    "async_lock",
)
