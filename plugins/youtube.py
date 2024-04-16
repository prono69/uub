# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}yta <(youtube/any) link>`
   Download audio from the link.

• `{i}ytv <(youtube/any) link>`
   Download video  from the link.

• `{i}ytsa <(youtube) search query>`
   Search and download audio from youtube.

• `{i}ytsv <(youtube) search query>`
   Search and download video from youtube.
"""

import asyncio
import time

from pyUltroid.fns.ytdl import download_yt, get_yt_link

from . import get_string, string_is_url, ultroid_cmd


@ultroid_cmd(
    pattern="yt(a|v|sa|sv) ?(.*)",
)
async def download_from_youtube(event):
    ytd = {"folder": f"resources/temp/{time.time()}"}
    video_opts = {
        "format": "bestvideo+bestaudio",
        "postprocessors": [{"key": "FFmpegMetadata"}],
        "merge_output_format": "mp4/mkv/flv",
    }
    audio_opts = {
        "format": "bestaudio",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3/m4a/ogg",
                "preferredquality": "256",
            },
            {"key": "FFmpegMetadata"},
        ],
    }
    opt = event.pattern_match.group(1)
    xx = await event.eor(get_string("com_1"))

    if opt == "a":
        ytd |= audio_opts
        url = event.pattern_match.group(2)
        if not url:
            return await xx.eor(get_string("youtube_1"))
        if not string_is_url(url):
            return await xx.eor(get_string("youtube_2"))

    elif opt == "v":
        ytd |= video_opts
        url = event.pattern_match.group(2)
        if not url:
            return await xx.eor(get_string("youtube_3"))
        if not string_is_url(url):
            return await xx.eor(get_string("youtube_4"))

    elif opt == "sa":
        ytd |= audio_opts
        query = event.pattern_match.group(2)
        if not query:
            return await xx.eor(get_string("youtube_5"))
        url = await get_yt_link(query)
        if not url:
            return await xx.edit(get_string("unspl_1"))
        await xx.eor(get_string("youtube_6"))

    elif opt == "sv":
        ytd |= video_opts
        query = event.pattern_match.group(2)
        if not query:
            return await xx.eor(get_string("youtube_7"))
        url = await get_yt_link(query)
        if not url:
            return await xx.edit(get_string("unspl_1"))
        await xx.eor(get_string("youtube_8"))

    else:
        return

    await asyncio.sleep(2)
    await download_yt(xx, url, ytd)
