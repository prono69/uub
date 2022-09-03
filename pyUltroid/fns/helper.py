# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import asyncio
import math
import os
import re
import sys
import time
from traceback import format_exc
from urllib.parse import unquote
from urllib.request import urlretrieve

try:
    import aiohttp
except ImportError:
    aiohttp = None
    try:
        import requests
    except ImportError:
        requests = None

try:
    import aiofiles
except ImportError:
    aiofiles = None

try:
    import heroku3
except ImportError:
    heroku3 = None

try:
    from git import Repo
    from git.exc import GitCommandError  # InvalidGitRepositoryError, NoSuchPathError
except ImportError:
    Repo = None

import asyncio
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps

from telethon.helpers import _maybe_await
from telethon.tl import types
from telethon.utils import get_display_name, get_input_document

from .._misc import CMD_HELP
from .._misc._wrappers import eod, eor
from ..configs import Var
from . import *

from ..dB._core import ADDONS, HELP, LIST, LOADED

from ..version import ultroid_version
from .FastTelethon import download_file as downloadable
from .FastTelethon import upload_file as uploadable


def run_async(function):
    @wraps(function)
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() * 5),
            partial(function, *args, **kwargs),
        )

    return wrapper


# ~~~~~~~~~~~~~~~~~~~~ small funcs ~~~~~~~~~~~~~~~~~~~~ #


def make_mention(user, custom=None):
    if n := getattr(user, "username", None):
        return "@" + n
    return inline_mention(user, custom=custom)


async def msg_link(message):
    chat = await message.get_chat()
    if isinstance(chat, types.User):
        user = "tg://openmessage?user_id={user_id}&message_id={msg_id}"
        return user.format(user_id=chat.id, msg_id=message.id)
    # will add others types later..
    return message.message_link


def inline_mention(user, custom=None, html=False):
    mention_text = get_display_name(user) or "Deleted Account" if not custom else custom
    if isinstance(user, types.User):
        if html:
            return f"<a href=tg://user?id={user.id}>{mention_text}</a>"
        return f"[{mention_text}](tg://user?id={user.id})"
    if isinstance(user, types.Channel) and user.username:
        if html:
            return f"<a href=https://t.me/{user.username}>{mention_text}</a>"
        return f"[{mention_text}](https://t.me/{user.username})"
    return mention_text


# ----------------- Load \\ Unloader ---------------- #


def un_plug(shortname):
    from .. import asst, ultroid_bot

    try:
        all_func = LOADED[shortname]
        for client in [ultroid_bot, asst]:
            for x, _ in client.list_event_handlers():
                if x in all_func:
                    client.remove_event_handler(x)
        del LOADED[shortname]
        del LIST[shortname]
        ADDONS.remove(shortname)
    except (ValueError, KeyError):
        name = f"addons.{shortname}"
        for client in [ultroid_bot, asst]:
            for i in reversed(range(len(client._event_builders))):
                ev, cb = client._event_builders[i]
                if cb.__module__ == name:
                    del client._event_builders[i]
                    try:
                        del LOADED[shortname]
                        del LIST[shortname]
                        ADDONS.remove(shortname)
                    except KeyError:
                        pass


async def safeinstall(event):
    from .. import HNDLR
    from ..startup.utils import load_addons

    if not event.reply_to:
        return await eod(
            event, f"Please use `{HNDLR}install` as reply to a .py file."
        )
    ok = await eor(event, "`Installing...`")
    reply = await event.get_reply_message()
    if not (
        reply.media
        and hasattr(reply.media, "document")
        and reply.file.name
        and reply.file.name.endswith(".py")
    ):
        return await eod(ok, "`Please reply to any python plugin`")
    plug = reply.file.name.replace(".py", "")
    if plug in list(LOADED):
        return await eod(ok, f"Plugin `{plug}` is already installed.")
    sm = reply.file.name.replace("_", "-").replace("|", "-")
    dl = await reply.download_media(f"addons/{sm}")
    if event.text[9:] != "f":
        read = open(dl).read()
        for dan in KEEP_SAFE().All:
            if re.search(dan, read):
                os.remove(dl)
                return await ok.edit(
                    f"**Installation Aborted.**\n**Reason:** Occurance of `{dan}` in `{reply.file.name}`.\n\nIf you trust the provider and/or know what you're doing, use `{HNDLR}install f` to force install.",
                )
    try:
        load_addons(dl)  # dl.split("/")[-1].replace(".py", ""))
    except BaseException:
        os.remove(dl)
        return await eor(ok, f"**ERROR**\n\n`{format_exc()}`", time=30)

    plug = sm.replace(".py", "")
    if plug in HELP:
        output = "**Plugin** - `{}`\n".format(plug)
        for i in HELP[plug]:
            output += i
        output += "\n© @TeamUltroid"
        await eod(ok, f"✓ `Ultroid - Installed`: `{plug}` ✓\n\n{output}")
    elif plug in CMD_HELP:
        output = f"Plugin Name-{plug}\n\n✘ Commands Available-\n\n"
        output += str(CMD_HELP[plug])
        await eod(ok, f"✓ `Ultroid - Installed`: `{plug}` ✓\n\n{output}")
    else:
        try:
            x = f"Plugin Name-{plug}\n\n✘ Commands Available-\n\n"
            for d in LIST[plug]:
                x += HNDLR + d + "\n"
            await eod(ok, f"✓ `Ultroid - Installed`: `{plug}` ✓\n\n`{x}`")
        except BaseException:
            await eod(ok, f"✓ `Ultroid - Installed`: `{plug}` ✓")


async def heroku_logs(event):
    """post heroku logs"""
    from .. import LOGS
    from ..heroku import Heroku

    xx = await eor(event, "`Processing...`")
    if err := Heroku.get("err"):
        return await xx.edit(err)
    try:
        ok = Heroku.get("app").get_log()
    except BaseException as er:
        LOGS.exception("Error getting Heroku Logs: ")
        await xx.edit("Something Wrong Occured!")

    if not aiohttp:
        with open("ultroid-heroku.log", "w") as log:
            log.write(ok)
    else:
        async with aiofiles.open("ultroid-heroku.log", "w") as log:
            await log.write(ok)
    await event.client.send_file(
        event.chat_id,
        file="ultroid-heroku.log",
        thumb="resources/extras/ultroid.jpg",
        caption="**Ultroid Heroku Logs.**",
    )

    os.remove("ultroid-heroku.log")
    await xx.delete()


async def def_logs(ult, file):
    await ult.client.send_file(
        ult.chat_id,
        file=file,
        thumb=ULTConfig.thumb,
        caption="**Ultroid Logs.**",
    )


async def updateme_requirements():
    await bash(
        f"{sys.executable} -m pip install --no-cache-dir -r requirements.txt"
    )


@run_async
def gen_chlog(repo, diff):
    """Generate Changelogs..."""
    UPSTREAM_REPO_URL = (
        Repo().remotes[0].config_reader.get("url").replace(".git", "")
    )
    ac_br = os.getenv("BRANCH")  # repo.active_branch.name
    ch_log = tldr_log = ""
    ch = f"<b>Ultroid {ultroid_version} updates for <a href={UPSTREAM_REPO_URL}/tree/{ac_br}>[{ac_br}]</a>:</b>"
    ch_tl = f"Ultroid {ultroid_version} updates for {ac_br}:"
    d_form = "%d/%m/%y || %H:%M"
    for c in repo.iter_commits(diff):
        ch_log += f"\n\n💬 <b>{c.count()}</b> 🗓 <b>[{c.committed_datetime.strftime(d_form)}]</b>\n<b><a href={UPSTREAM_REPO_URL.rstrip('/')}/commit/{c}>[{c.summary}]</a></b> 👨‍💻 <code>{c.author}</code>"
        tldr_log += f"\n\n💬 {c.count()} 🗓 [{c.committed_datetime.strftime(d_form)}]\n[{c.summary}] 👨‍💻 {c.author}"
    if ch_log:
        return str(ch + ch_log), str(ch_tl + tldr_log)
    return ch_log, tldr_log


# --------------------------------------------------------------------- #


async def bash(cmd, run_code=0):
    """run any command in subprocess and get output or error"""
    Shell = os.environ.get("SHELL", "/bin/bash")
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        executable=Shell,
    )
    stdout, stderr = await process.communicate()
    err = stderr.decode(errors="replace").strip() or None
    out = stdout.decode(errors="replace").strip()
    if not run_code and err:
        split = cmd.split()[0]
        if f"{split}: not found" in err:
            return out, f"{split.upper()}_NOT_FOUND"
    return out, err


async def cleargif(gif):
    from telethon.tl.functions.messages import SaveGifRequest
    from .. import LOGS, ultroid_bot

    try:
        await ultroid_bot(SaveGifRequest(id=get_input_document(gif), unsave=True))
    except Exception as ex:
        return LOGS.exception("'cleargif' exception")


# ---------------------------UPDATER-------------------------------- #

# Will add in class

async def updater():
    from .. import LOGS

    try:
        repo = Repo()
    except BaseException:
        LOGS.exception("Git Initialise error.")
        Repo().__del__()
        return

    # Git Hacks!
    ac_br = os.getenv("BRANCH")  # repo.active_branch.name
    ups_rem = repo.remote("upstream")
    ups_rem.fetch(ac_br)
    changelog, tl_chnglog = await gen_chlog(repo, f"HEAD..upstream/{ac_br}")
    return bool(changelog)

    """
    try:
        ups = repo.create_remote(
            "upstream", Repo().remotes[0].config_reader.get("url").replace(".git", "")
        )
    except GitCommandError:
        pass
    else:
        ups.fetch()
        repo.create_head("main", ups.refs.main)
        repo.heads.main.set_tracking_branch(ups.refs.main)
        repo.heads.main.checkout(True)
    """


# ----------------Fast Upload/Download----------------

# @1danish_00 @new-dev0 @buddhhu

async def uploader(file, name, taime, event, msg):
    with open(file, "rb") as f:
        result = await uploadable(
            client=event.client,
            file=f,
            filename=name,
            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                progress(
                    d,
                    t,
                    event,
                    taime,
                    msg,
                ),
            ),
        )
    return result


async def downloader(filename, file, event, taime, msg):
    with open(filename, "wb") as fk:
        result = await downloadable(
            client=event.client,
            location=file,
            out=fk,
            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                progress(
                    d,
                    t,
                    event,
                    taime,
                    msg,
                ),
            ),
        )
    return result


# ~~~~~~~~~~~~~~~~~~~~DDL Downloader~~~~~~~~~~~~~~~~~~~~
# @buddhhu @new-dev0


async def download_file(link, name):
    """for files, without progress callback with aiohttp"""
    if aiohttp:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(link) as re_ses:
                with open(name, "wb") as file:
                    file.write(await re_ses.read())
    elif requests:
        content = requests.get(link).content
        with open(name, "wb") as file:
            file.write(content)
    else:
        raise Exception("Aiohttp or requests is not installed.")
    return name


async def fast_download(download_url, filename=None, progress_callback=None):
    if not aiohttp:
        return await download_file(download_url, filename)
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url, timeout=None) as response:
            if not filename:
                filename = unquote(download_url.rpartition("/")[-1])
            total_size = int(response.headers.get("content-length", 0)) or None
            downloaded_size = 0
            start_time = time.time()
            with open(filename, "wb") as f:
                async for chunk in response.content.iter_chunked(1024):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                    if progress_callback and total_size:
                        await _maybe_await(
                            progress_callback(downloaded_size, total_size)
                        )
            return filename, time.time() - start_time


# --------------------------Media Funcs-------------------------------- #


def mediainfo(media):
    xx = str((str(media)).split("(", maxsplit=1)[0])
    m = ""
    if xx == "MessageMediaDocument":
        mim = media.document.mime_type
        if mim == "application/x-tgsticker":
            m = "sticker animated"
        elif "image" in mim:
            if mim == "image/webp":
                m = "sticker"
            elif mim == "image/gif":
                m = "gif as doc"
            else:
                m = "pic as doc"
        elif "video" in mim:
            if "DocumentAttributeAnimated" in str(media):
                m = "gif"
            elif "DocumentAttributeVideo" in str(media):
                i = str(media.document.attributes[0])
                if "supports_streaming=True" in i:
                    m = "video"
                m = "video as doc"
            else:
                m = "video"
        elif "audio" in mim:
            m = "audio"
        else:
            m = "document"
    elif xx == "MessageMediaPhoto":
        m = "pic"
    elif xx == "MessageMediaWebPage":
        m = "web"
    return m


# ------------------Some Small Funcs----------------


async def asyncread(file):
    if not aiofiles:
        with open(file, "r+") as f:
            lx = f.read()
    else:
        async with aiofiles.open(file, "r+") as f:
            lx = await f.read()
    return lx


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


def humanbytes(size):
    if not size:
        return "0 B"
    for unit in ["", "K", "M", "G", "T"]:
        if size < 1024:
            break
        size /= 1024
    if isinstance(size, int):
        size = f"{size}{unit}B"
    elif isinstance(size, float):
        size = f"{size:.2f}{unit}B"
    return size


def numerize(number):
    if not number:
        return None
    for unit in ["", "K", "M", "B", "T"]:
        if number < 1000:
            break
        number /= 1000
    if isinstance(number, int):
        number = f"{number}{unit}"
    elif isinstance(number, float):
        number = f"{number:.2f}{unit}"
    return number


No_Flood = {}


async def progress(current, total, event, start, type_of_ps, file_name=None):
    jost = str(event.chat_id) + "_" + str(event.id)
    plog = No_Flood.get(jost)
    now = time.time()
    if plog and current != total:
        if (now - plog) < 8:  # delay = 8s
            return
    diff = now - start
    percentage = current * 100 / total
    speed = current / diff
    time_to_completion = round((total - current) / speed) * 1000
    progress_str = "`[{0}{1}] {2}%`\n\n".format(
        "".join("●" for i in range(math.floor(percentage / 5))),
        "".join("" for i in range(20 - math.floor(percentage / 5))),
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
        No_Flood.update({jost: now})
        await event.edit(to_edit)
    except MessageNotModifiedError as exc:
        from .. import LOGS

        LOGS.exception("err in progress: message_not_modified")


# ------------------System\\Heroku stuff----------------
# @xditya @sppidy @techierror


async def restart(ult=None, EDIT=False):
    from .. import HOSTED_ON, LOGS

    if HOSTED_ON == "heroku":
        from ..heroku import Heroku

        if err := Heroku.get("err"):
            return await eor(ult, err)
        if EDIT:
            ult = await ult.edit("`Restarting your app, please wait for a minute!`")
        try:
            Heroku.get("app").restart()
        except BaseException as er:
            LOGS.exception(er)
            await ult.eor("Something Wrong Occured!")
    else:
        if len(sys.argv) == 1:
            os.execl(sys.executable, sys.executable, "-m", "pyUltroid")
        else:
            os.execl(
                sys.executable,
                sys.executable,
                "-m",
                "pyUltroid",
                sys.argv[1],
                sys.argv[2],
                sys.argv[3],
                sys.argv[4],
                sys.argv[5],
                sys.argv[6],
            )


async def shutdown(ult):
    from .. import HOSTED_ON, LOGS

    ult = await eor(ult, "Shutting Down")
    if HOSTED_ON == "heroku":
        from ..heroku import Heroku

        if err := Heroku.get("err"):
            return await eor(ult, err)
        try:
            dynotype = os.getenv("DYNO").split(".")[0]
            Heroku.get("app").process_formation()[dynotype].scale(0)
        except BaseException as er:
            LOGS.exception(er)
            await ult.eor("Something Wrong Occured!")
    else:
        sys.exit()


class getFlags:
    """Extract flags from string."""

    def __init__(
        self,
        text,
        seperator=" ",
        args_seperator="-",
        kwargs_seperator="=",
        merge_args=False,
        convert=True,
        cmds=False,
        original=False,
    ):
        self.text = text
        self.seperator = seperator
        self.args_seperator = args_seperator
        self.kwargs_seperator = kwargs_seperator
        self.merge_args = merge_args
        # combines all args into one
        self.convert = convert
        self.cmds = cmds
        self.original = original

    @property
    def args(self):
        return self.flags[0]

    @property
    def kwargs(self):
        return self.flags[1]

    @property
    def flags(self):
        spl = self.splitter(self.text)
        return self.sep_args_kwargs(spl)

    def splitter(self, text: str):
        from string import punctuation

        text = str(text)
        sep_lst = text.split(self.seperator)
        if self.cmds:
            return sep_lst
        return sep_lst[1:] if sep_lst[0][0] in set(punctuation) else sep_lst

    def sep_args_kwargs(self, text_lst: list):
        kwargs, args = {}, []
        for txt in text_lst:
            if not txt:
                continue
            elif txt.startswith(self.args_seperator) and len(txt.rstrip()) > 1:
                if self.kwargs_seperator in txt:
                    fms = txt.split(self.kwargs_seperator)
                    value_ = fms[1]
                    key_ = fms[0] if self.original else fms[0][1:]
                    if self.convert:
                        # key_ = getFlags.change_types(key_)
                        value_ = getFlags.change_types(value_)
                    kwargs[key_] = value_
                else:
                    txt = txt if self.original else txt[1:]
                    key_ = getFlags.change_types(txt) if self.convert else txt
                    kwargs[key_] = True
            else:
                args.append(txt)
        if self.merge_args:
            args = [self.seperator.join(args)]
        return args, kwargs

    @staticmethod
    def change_types(text):
        try:
            text = literal_eval(str(text))
        except BaseException:
            pass
        return text

