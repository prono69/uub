# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import asyncio
import os
import re
import sys
import time
from pathlib import Path
from traceback import format_exc
# from urllib.request import urlretrieve

from telethon.helpers import _maybe_await
from telethon.tl import types
from telethon.utils import get_display_name

from pyUltroid import *
from pyUltroid._misc import CMD_HELP
from pyUltroid._misc._wrappers import eod, eor
from pyUltroid.custom.commons import *
from pyUltroid.custom.commons import aiohttp_client
from pyUltroid.dB._core import ADDONS, HELP, LIST, LOADED
from pyUltroid.version import ultroid_version
from pyUltroid.exceptions import DownloadError, UploadError
from pyUltroid.custom.FastTelethon import download_file, upload_file

try:
    import heroku3
except ImportError:
    heroku3 = None

try:
    from git import Repo
    from git.exc import GitCommandError  # InvalidGitRepositoryError, NoSuchPathError
except ImportError:
    Repo = None


# ~~~~~~~~~~~~~~~~~~~~ small funcs ~~~~~~~~~~~~~~~~~~~~ #


def make_mention(user, custom=None):
    if n := getattr(user, "username", None):
        return "@" + n
    return inline_mention(user, custom=custom)


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
    from pyUltroid import asst, ultroid_bot

    try:
        name = f"addons.{shortname}"
        all_func = LOADED[shortname]
        for client in (ultroid_bot, asst):
            for x, _ in client.list_event_handlers()[::-1]:
                if x in all_func:
                    client.remove_event_handler(x)
        LOADED.pop(shortname, None)
        LIST.pop(shortname, None)
        ADDONS.remove(shortname)
    except (ValueError, KeyError):
        for client in (ultroid_bot, asst):
            builders = client._event_builders
            for i in range(len(builders) - 1, -1, -1):
                ev, cb = builders[i]
                if cb.__module__ == name:
                    try:
                        LOADED.pop(shortname, None)
                        LIST.pop(shortname, None)
                        del client._event_builders[i]
                        ADDONS.remove(shortname)
                    except (ValueError, IndexError, KeyError):
                        pass
    finally:
        sys.modules.pop(name, None)


async def safeinstall(event):
    from pyUltroid import HNDLR
    from pyUltroid.startup.utils import load_addons

    if not event.reply_to:
        return await eod(event, f"Please use `{HNDLR}install` as reply to a .py file.")
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
    if event.text[9:] != "f" and KEEP_SAFE:
        read = await asyncread(dl)
        for dan in KEEP_SAFE().All:
            if re.search(dan, read):
                osremove(dl)
                return await ok.edit(
                    f"**Installation Aborted.**\n**Reason:** Occurance of `{dan}` in `{reply.file.name}`.\n\nIf you trust the provider and/or know what you're doing, use `{HNDLR}install f` to force install.",
                )

    try:
        load_addons(dl)  # dl.split("/")[-1].replace(".py", ""))
    except BaseException:
        osremove(dl)
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
    from pyUltroid.custom.heroku import Heroku

    xx = await eor(event, "`Processing...`")
    if err := Heroku.get("err"):
        return await xx.edit(err)
    try:
        ok = Heroku.get("app").get_log()
    except BaseException as er:
        LOGS.exception("Error getting Heroku Logs: ")
        return await xx.edit("Something Wrong Occured!")

    filename = check_filename("ultroid-heroku-logs.txt")
    await asyncwrite(filename, ok, mode="w+")
    await event.client.send_file(
        event.chat_id,
        file=filename,
        thumb="resources/extras/ultroid.jpg",
        caption="**Ultroid Heroku Logs.**",
    )
    osremove(filename)
    await xx.delete()


# --------------------------------------------------------------------- #


async def def_logs(ult, file):
    await ult.client.send_file(
        ult.chat_id,
        file=file,
        thumb=ULTConfig.thumb,
        caption="**Ultroid Logs!**",
    )


@run_async
def gen_chlog(repo, diff):
    """Generate Changelogs..."""
    UPSTREAM_REPO_URL = repo.remote("origin").config_reader.get("url")
    ac_br = repo.active_branch.name
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


# ---------------------------UPDATER-------------------------------- #


async def updater():
    try:
        repo = Repo()
        origin_remote = repo.remote("origin")
    except BaseException:
        LOGS.exception("Git Initialise error.")
        Repo().__del__()
        return

    # Git Hacks!
    try:
        upstream_remote = repo.remote("upstream")
    except ValueError:
        repo.create_remote("upstream", origin_remote.config_reader.get("url"))
        upstream_remote = repo.remote("upstream")

    # upstream_remote.fetch()
    branch = repo.active_branch.name
    upstream_remote.fetch(branch)
    changelog, tl_chnglog = await gen_chlog(repo, f"HEAD..upstream/{branch}")
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


# ---------------- Fast Upload/Download ----------------

# @1danish_00 @new-dev0 @buddhhu

"""
# alternative -> client.fast_download/upload

async def uploader(file, name, taime, event, msg):
    edit_missed = 0
    with open(file, "rb") as f:
        try:
            result = await upload_file(
                client=event.client,
                file=f,
                filename=name,
                progress_callback=lambda d, t: loop.create_task(
                    progress(
                        d,
                        t,
                        event,
                        taime,
                        msg,
                    ),
                ),
            )
        except MessageNotModifiedError as exc:
            edit_missed += 1
            if edit_missed >= 6:
                raise UploadError(str(exc)) from None
        except MessageIdInvalidError:
            raise UploadError(
                f"Upload Cancelled for '{name}' because message was deleted."
            ) from None

    return result


async def downloader(filename, file, event, taime, msg):
    edit_missed = 0
    with open(filename, "wb") as fk:
        try:
            result = await download_file(
                client=event.client,
                location=file,
                out=fk,
                progress_callback=lambda d, t: loop.create_task(
                    progress(
                        d,
                        t,
                        event,
                        taime,
                        msg,
                    ),
                ),
            )
        except MessageNotModifiedError as exc:
            edit_missed += 1
            if edit_missed >= 6:
                raise DownloadError(str(exc)) from None
        except MessageIdInvalidError:
            raise DownloadError(
                f"Dowload Cancelled for '{filename}' because message was deleted."
            ) from None

    return result
"""


async def tg_downloader(
    media,
    event,
    show_progress=False,
    filename=None,
    **kwargs,
):
    assert media.media and mediainfo(media.media) not in (
        "",
        "web",
    ), "Wrong Media type to Download.."
    if getattr(media.media, "document", None):
        if filename:
            if Path(filename).is_dir():
                filename = str(Path(filename) / get_tg_filename(media))
        else:
            filename = "resources/downloads/" + get_tg_filename(media)
        dlxx = await event.client.fast_downloader(
            media.document,
            event=event,
            filename=filename,
            show_progress=show_progress,
            **kwargs,
        )
        return dlxx[0].name, dlxx[1]

    s_time = time.time()
    _callback = None
    if show_progress and not getattr(media, "photo", None):
        _callback = lambda d, t: asyncio.create_task(
            progress(d, t, event, s_time, "Downloading ...")
        )
    path = await event.client.download_media(
        media,
        filename,
        progress_callback=_callback,
    )
    return path, time.time() - s_time


# ~~~~~~~~~~~~~~~~~ DDL Downloader ~~~~~~~~~~~~~~~~
# @buddhhu @new-dev0


async def download_file(link, name, validate=False):
    """for files, without progress callback with aiohttp"""
    name = check_filename(name)

    if aiohttp_client:

        async def _download(response):
            if validate and "application/json" in response.headers.get("Content-Type"):
                return None, await response.json()
            async for chunk in response.content.iter_chunked(256 * 1024):
                if chunk:
                    await asyncwrite(name, chunk, mode="ab+")
            return name, ""
    else:

        def _download(response):
            if validate and "application/json" in response.headers.get("Content-Type"):
                return None, response.json()
            for chunk in response.iter_content(chunk_size=256 * 1024):
                if chunk:
                    with open(name, "ab+") as f:
                        f.write(chunk)
            return name, ""

    return await async_searcher(link, evaluate=_download)


async def fast_download(download_url, filename=None, progress_callback=None):
    if not filename:
        filename = get_filename_from_url(download_url)
        filename = check_filename(Path("resources/downloads") / filename)

    start_time = time.time()
    if not aiohttp_client:
        # without progress callback..
        dl = await download_file(download_url, filename)
        return dl[0], time.time() - start_time

    async with aiohttp_client() as session:
        async with session.get(download_url, timeout=None) as response:
            total_size = int(response.headers.get("content-length", 0)) or None
            downloaded_size = 0
            start_time = time.time()
            async for chunk in response.content.iter_chunked(256 * 1024):
                if chunk:
                    await asyncwrite(filename, chunk, mode="ab+")
                    downloaded_size += len(chunk)
                if progress_callback and total_size:
                    await _maybe_await(progress_callback(downloaded_size, total_size))
            return filename, time.time() - start_time


# ----------------- Media Funcs ------------------------- #


def mediainfo(media):
    if isinstance(media, types.MessageMediaDocument):
        mime = media.document.mime_type
        if mime == "application/x-tgsticker":
            return "sticker animated"
        elif "video" in mime:
            attrs = getattr(media.document, "attributes", None)
            if attrs and any(
                isinstance(i, types.DocumentAttributeAnimated) for i in attrs
            ):
                return "gif"
            elif attrs and any(
                isinstance(i, types.DocumentAttributeSticker) for i in attrs
            ):
                return "sticker video"
            streamable = (
                getattr(attrs[0], "supports_streaming", None) if attrs else None
            )
            return "video" if streamable else "video as doc"
        elif "image" in mime:
            if mime == "image/webp":
                return "sticker"
            elif mime == "image/gif":
                return "gif as doc"
            else:
                return "pic as doc"
        elif "audio" in mime:
            return "audio"
        return "document"
    elif isinstance(media, types.MessageMediaPhoto):
        return "pic"
    elif isinstance(media, types.MessageMediaWebPage):
        return "web"
    else:
        return ""


# ------------------Some Small Funcs----------------


def numerize(number):
    if not number:
        return None
    unit = ""
    for unit in ("", "K", "M", "B", "T"):
        if number < 1000:
            break
        number /= 1000
    if isinstance(number, int):
        number = f"{number}{unit}"
    elif isinstance(number, float):
        number = f"{number:.2f}{unit}"
    return number


# ------------------System\\Heroku stuff----------------
# @xditya @sppidy @techierror


async def restart(ult=None, edit=False):
    from pyUltroid import HOSTED_ON, ultroid_bot

    if edit and ult:
        ult = await ult.eor("`Restarting your app, please wait for a minute!`")

    if HOSTED_ON == "heroku":
        from pyUltroid.custom.heroku import Heroku

        if err := Heroku.get("err"):
            if ult and edit:
                await ult.edit(err)
            return
        try:
            Heroku.get("app").restart()
        except Exception as er:
            LOGS.exception(er)
            if ult and edit:
                await ult.edit(
                    "Something Wrong happened while restarting your heroku app"
                )
    else:
        await ultroid_bot.disconnect()


async def shutdown(ult):
    from pyUltroid import HOSTED_ON, ultroid_bot

    ult = await ult.eor("`Shutting Down..`")
    if HOSTED_ON == "heroku":
        from pyUltroid.custom.heroku import Heroku

        if err := Heroku.get("err"):
            return await ult.edit(err)
        try:
            dynotype = os.getenv("DYNO").split(".")[0]
            Heroku.get("app").process_formation()[dynotype].scale(0)
        except BaseException as er:
            LOGS.exception(er)
            await ult.edit(
                "Something Wrong happened while shuttig down your Heroku app."
            )
    else:
        await ultroid_bot.disconnect()


__all__ = (
    "def_logs",
    "download_file",
    "fast_download",
    "gen_chlog",
    "heroku_logs",
    "inline_mention",
    "make_mention",
    "mediainfo",
    "numerize",
    "progress",
    "restart",
    "safeinstall",
    "shutdown",
    "tg_downloader",
    "un_plug",
    "updater",
)
