# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.


from . import get_help

__doc__ = get_help("help_compressor")


import asyncio
import math
import os
import re
import time
from datetime import datetime as dt

from telethon.errors.rpcerrorlist import MessageNotModifiedError, MessageIdInvalidError

from . import (
    LOGS,
    asyncread,
    bash,
    check_filename,
    get_string,
    getFlags,
    humanbytes,
    mediainfo,
    media_info,
    shq,
    time_formatter,
    ultroid_cmd,
    osremove,
)


CMDS = {
    "x265": (
        "ffmpeg -hide_banner -loglevel error -progress {} -i {} -preset ultrafast -vcodec libx265 -crf {} -c:a copy -c:s copy {} -y",
        28,
    ),
    "x264": (
        "ffmpeg -hide_banner -loglevel error -progress {} -i {} -preset superfast -vcodec libx264 -crf {} -c:a copy -c:s copy {} -y",
        36,
    ),
}


@ultroid_cmd(pattern="x?compress ?(.*)")
async def compressor(e):
    xxx = await e.eor("Checking...")
    args = getFlags(e.text, merge_args=True)
    q = "x264" if "x" in e.text[:4] else "x265"
    crf = args.kwargs.pop("c", CMDS[q][1])
    vido = await e.get_reply_message()

    if not vido and bool(args.args):
        path = args.args[0]
        if not os.path.exists(path):
            return await xxx.edit("Path not found")
        to_delete, reply_to = False, e.id
        await xxx.edit(f"`Found Path {path}\n\nNow Compressing...`")

    elif vido and vido.media and "video" in mediainfo(vido.media):
        from pyUltroid.fns._transfer import pyroDL

        await xxx.edit(get_string("audiotools_5"))
        dlx = pyroDL(event=xxx, source=vido)
        path = await dlx.download(_log=False, auto_edit=False, **args.kwargs)
        if isinstance(path, Exception):
            return await xxx.edit("#Error in downloading file: {path}")
        to_delete, reply_to = True, vido.id
        await xxx.edit(
            f"`Downloaded {path} of {humanbytes(os.path.getsize(path))} in {dlx.dl_time}... \n\nNow Compressing...`"
        )
    else:
        return await xxx.eor(get_string("audiotools_8"), time=8)

    # Starting Compress!
    c_time = time.time()
    o_size = os.path.getsize(path)
    out = check_filename(os.path.splitext(path)[0] + f"_compressed_{q}_{crf}.mkv")
    slp_time = 10 if e.client._bot else 8

    # x, y = await bash(f'''mediainfo --fullscan {shq(path)} | grep "Frame count"''')
    # total_frames = x.split(":")[1].split("\n")[0]
    total_frames = media_info(path).get("frames")
    progress = f"progress-{c_time}.txt"
    with open(progress, "w+") as hmm:
        pass

    proce = await asyncio.create_subprocess_shell(
        CMDS[q][0].format(shq(progress), shq(path), str(crf), shq(out)),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    while proce.returncode != 0:
        speed = 0
        await asyncio.sleep(slp_time)
        text = await asyncread(progress)
        frames = re.findall("frame=(\\d+)", text)
        size = re.findall("total_size=(\\d+)", text)
        del text
        if len(frames):
            elapse = int(frames[-1])
        if len(size):
            size = int(size[-1])
            per = elapse * 100 / int(total_frames)
            time_diff = time.time() - int(c_time)
            speed = round(elapse / time_diff, 2)
        if int(speed) != 0:
            some_eta = ((int(total_frames) - elapse) / speed) * 1000
            text = f"`Compressing {os.path.basename(out)} at {crf} CRF` \n"
            progress_str = "`[{0}{1}] {2}%` \n\n".format(
                "".join("●" for i in range(math.floor(per / 5))),
                "".join("" for i in range(20 - math.floor(per / 5))),
                round(per, 2),
            )

            e_size = f"**Done ~**  `{humanbytes(size)}` \n"
            eta = f"**ETA ~**  `{time_formatter(some_eta)}`"
            try:
                await xxx.edit(text + progress_str + e_size + eta)
            except MessageNotModifiedError:
                LOGS.exception("Compressor edit err:")
            except MessageIdInvalidError:
                await asyncio.sleep(3)
                n = [progress, out]
                if to_delete:
                    n.append(path)
                return osremove(n)

    # Uploader
    if to_delete:
        osremove(path)
    c_size = os.path.getsize(out)
    difff = time_formatter((time.time() - c_time) * 1000)
    osremove(progress)
    await xxx.edit(
        f"`Compressed {humanbytes(o_size)} to {humanbytes(c_size)} in {difff}\nTrying to Upload...`"
    )
    differ = 100 - ((c_size / o_size) * 100)
    caption = (
        f"**Original Size: **`{humanbytes(o_size)}`\n"
        f"**Compressed Size: **`{humanbytes(c_size)}`\n"
        f"**Compression Ratio: **`{differ:.2f}%`\n"
        f"\n**Time Taken To Compress: **`{difff}`"
    )
    from pyUltroid.fns._transfer import pyroUL

    x = pyroUL(event=xxx, _path=out)
    await x.upload(
        caption=caption, delete_file=True, reply_to=reply_to, _log=False, **args.kwargs,
    )
