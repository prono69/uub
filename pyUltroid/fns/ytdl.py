# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import glob
import os
import re
import time

from telethon import Button
from yt_dlp import YoutubeDL

from .. import LOGS, udB
from .helper import download_file, humanbytes, osremove, run_async, time_formatter
from pyUltroid.custom._transfer import pyroUL, pyroDL

try:
    from youtubesearchpython import Playlist, VideosSearch
except ImportError:
    Playlist, VideosSearch = None, None


async def ytdl_progress(k, start_time, event):
    if k["status"] == "error":
        return await event.edit("error")
    while k["status"] == "downloading":
        text = (
            f"`Downloading: {k['filename']}\n"
            + f"Total Size: {humanbytes(k['total_bytes'])}\n"
            + f"Downloaded: {humanbytes(k['downloaded_bytes'])}\n"
            + f"Speed: {humanbytes(k['speed'])}/s\n"
            + f"ETA: {time_formatter(k['eta']*1000)}`"
        )
        if round((time.time() - start_time) % 10.0) == 0:
            try:
                await event.edit(text)
            except Exception as ex:
                LOGS.error(f"ytdl_progress: {ex}")


def get_yt_link(query):
    search = VideosSearch(query, limit=1).result()
    try:
        return search["result"][0]["link"]
    except IndexError:
        return


async def download_yt(event, link, ytd):
    reply_to = event.reply_to_msg_id or event
    info = await dler(event, link, ytd, download=True)
    if not info:
        return
    if info.get("_type", None) == "playlist":
        total = info["playlist_count"]
        for num, file in enumerate(info["entries"]):
            num += 1
            id_ = file["id"]
            title = file["title"]
            thumb, _ = await download_file(
                file.get("thumbnail", None) or file["thumbnails"][-1]["url"],
                id_ + ".jpg",
            )
            if not (file := yt_helper(id_, title)):
                return LOGS.error(f"YTDL ERROR: file not found: {id_}")
            if file.endswith(".part"):
                osremove(file, thumb)
                await event.client.send_message(
                    event.chat_id,
                    f"`[{num}/{total}]` `Invalid Video format.\nIgnoring that...`",
                )
                return
            from_ = info["extractor"].split(":")[0]
            caption = f"`[{num}/{total}]` `{title}`\n\n`from {from_}`"
            ulx = pyroUL(event=event, _path=file)
            await ulx.upload(
                delay=6,
                thumb=thumb,
                to_delete=True,
                caption=caption,
                auto_edit=False,
                reply_to=reply_to,
            )
        await event.try_delete()
        return

    title = info["title"]  # [:50]
    id_ = info["id"]
    thumb, _ = await download_file(
        info.get("thumbnail", None) or f"https://i.ytimg.com/vi/{id_}/hqdefault.jpg",
        id_ + ".jpg",
    )
    if not (file := yt_helper(id_, title)):
        return LOGS.error(f"YTDL ERROR: file not found: {id_}")
    ulx = pyroUL(event=event, _path=file)
    await ulx.upload(
        delay=6,
        thumb=thumb,
        to_delete=True,
        auto_edit=False,
        reply_to=reply_to,
        caption=f"```{title}```",
    )
    await event.try_delete()


# ---------------YouTube Downloader Inline---------------
# @New-Dev0 @buddhhu @1danish-00


def get_formats(type, id, data):
    if type == "audio":
        audio = []
        for _quality in ("64", "128", "256", "320"):
            _audio = {}
            _audio.update(
                {
                    "ytid": id,
                    "type": "audio",
                    "id": _quality,
                    "quality": _quality + "KBPS",
                }
            )
            audio.append(_audio)
        return audio
    if type == "video":
        video = []
        size = 0
        for vid in data["formats"]:
            if vid["format_id"] == "251":
                size += vid["filesize"] if vid.get("filesize") else 0
            if vid["vcodec"] != "none":
                _id = int(vid["format_id"])
                _quality = str(vid["width"]) + "×" + str(vid["height"])
                _size = size + (vid["filesize"] if vid.get("filesize") else 0)
                _ext = "mkv" if vid["ext"] == "webm" else "mp4"
                if _size < 2147483648:  # Telegram's Limit of 2GB
                    _video = {}
                    _video.update(
                        {
                            "ytid": id,
                            "type": "video",
                            "id": str(_id) + "+251",
                            "quality": _quality,
                            "size": _size,
                            "ext": _ext,
                        }
                    )
                    video.append(_video)
        return video
    return []


def get_buttons(listt):
    id = listt[0]["ytid"]
    butts = [
        Button.inline(
            text=f"[{x['quality']}"
            + (f" {humanbytes(x['size'])}]" if x.get("size") else "]"),
            data=f"ytdownload:{x['type']}:{x['id']}:{x['ytid']}"
            + (f":{x['ext']}" if x.get("ext") else ""),
        )
        for x in listt
    ]
    buttons = list(zip(butts[::2], butts[1::2]))
    if len(butts) % 2 == 1:
        buttons.append((butts[-1],))
    buttons.append([Button.inline("« Back", f"ytdl_back:{id}")])
    return buttons


async def dler(event, url, opts: dict = {}, download=False):
    await event.edit("`Getting Data...`")
    if "quiet" not in opts:
        opts["quiet"] = True
    opts["username"] = udB.get_key("YT_USERNAME")
    opts["password"] = udB.get_key("YT_PASSWORD")
    if download:
        await ytdownload(url, opts)
    try:
        return await extract_info(url, opts)
    except Exception as e:
        await event.edit(f"{type(e)}: {e}")
        return


@run_async
def ytdownload(url, opts):
    try:
        return YoutubeDL(opts).download([url])
    except Exception as ex:
        LOGS.error(ex)


@run_async
def extract_info(url, opts):
    return YoutubeDL(opts).extract_info(url=url, download=False)


@run_async
def get_videos_link(url):
    to_return = []
    regex = re.search(r"\?list=([(\w+)\-]*)", url)
    if not regex:
        return to_return
    playlist_id = regex.group(1)
    videos = Playlist(playlist_id)
    for vid in videos.videos:
        link = re.search(r"\?v=([(\w+)\-]*)", vid["link"]).group(1)
        to_return.append(f"https://youtube.com/watch?v={link}")
    return to_return


def yt_helper(yt_id, title):
    exts = (
        ".webm",
        ".mkv",
        ".mp4",
        ".3gp",
        ".mp3",
        ".m4a",
        ".flv",
        ".aac",
    )
    for file in os.listdir("."):
        if file.startswith(yt_id):
            if file.endswith(".part"):
                return file
            for ext in exts:
                if file.lower().endswith(ext):
                    fn = check_filename(title + "." + file.split(".", maxsplit=1)[1])
                    os.rename(file, fn)
                    return fn
