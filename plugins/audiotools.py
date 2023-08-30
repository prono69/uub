# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

import asyncio
import time
from datetime import datetime as dt
from pathlib import Path
from shlex import quote

from pyUltroid.fns.tools import set_attributes

from . import (
    LOGS,
    ULTConfig,
    bash,
    check_filename,
    downloader,
    eod,
    eor,
    genss,
    get_help,
    get_string,
    humanbytes,
    mediainfo,
    osremove,
    stdr,
    time_formatter,
    ultroid_cmd,
    uploader,
)

__doc__ = get_help("help_audiotools")


@ultroid_cmd(pattern="makevoice$")
async def to_voice(e):
    reply = await e.get_reply_message()
    if not (reply and reply.media and mediainfo(reply.media) == "audio"):
        return await e.eor("`Reply to Audio file...`", time=5)

    eris = await e.eor("›› __Converting to Voice..__")
    try:
        dl = await e.client.fast_downloader(
            reply.document,
            show_progress=True,
            event=eris,
        )
        dl_path = dl[0].name
        opus_path = check_filename(Path(dl_path).with_suffix(".opus"))
        await eris.edit(get_string("audiotools_2"))
        cmd = f"ffmpeg -hide_banner -loglevel error -i {quote(dl_path)} -c:a libopus -b:a 64k -vbr on -compression_level 9 -application audio {quote(opus_path)} -y"
        await bash(cmd)
        await asyncio.sleep(2)
        tgfile, _ = await e.client.fast_uploader(
            opus_path,
            event=eris,
            show_progress=True,
        )
        osremove(dl_path, opus_path)
        caption = f"`{Path(opus_path).name}`"
        await e.client.send_file(
            e.chat_id,
            tgfile,
            voice_note=True,
            caption=caption,
            silent=e.reply_to,
            reply_to=e.reply_to_msg_id or e.id,
        )
        await eris.delete()
    except Exception as exc:
        LOGS.exception(exc)
        await eris.edit(f"**Error while Converting to Voice:** \n`{exc}`")


@ultroid_cmd(pattern="atrim( (.*)|$)")
async def trim_aud(e):
    sec = e.pattern_match.group(1).strip()
    if not sec or "-" not in sec:
        return await eod(e, get_string("audiotools_3"))
    a, b = sec.split("-")
    if int(a) >= int(b):
        return await eod(e, get_string("audiotools_4"))
    vido = await e.get_reply_message()
    if vido and vido.media and mediainfo(vido.media).startswith(("video", "audio")):
        if hasattr(vido.media, "document"):
            vfile = vido.media.document
            name = vido.file.name
        else:
            vfile = vido.media
            name = ""
        if not name:
            name = dt.now().isoformat("_", "seconds") + ".mp4"
        xxx = await e.eor(get_string("audiotools_5"))
        c_time = time.time()
        file = await downloader(
            f"resources/downloads/{name}",
            vfile,
            xxx,
            c_time,
            f"Downloading {name}...",
        )

        o_size = Path(file.name).stat().st_size
        d_time = time.time()
        diff = time_formatter((d_time - c_time) * 1000)
        file_name = (file.name).split("/")[-1]
        out = file_name.replace(file_name.split(".")[-1], "_trimmed.aac")
        if int(b) > int(await genss(file.name)):
            osremove(file.name)
            return await eod(xxx, get_string("audiotools_6"))
        ss, dd = stdr(int(a)), stdr(int(b))
        xxx = await xxx.edit(
            f"Downloaded `{file.name}` of `{humanbytes(o_size)}` in `{diff}`.\n\nNow Trimming Audio from `{ss}` to `{dd}`..."
        )
        cmd = f'ffmpeg -i "{file.name}" -preset ultrafast -ss {ss} -to {dd} -vn -acodec copy "{out}" -y'
        await bash(cmd)
        osremove(file.name)
        f_time = time.time()
        mmmm = await uploader(out, out, f_time, xxx, f"Uploading {out}...")
        attributes = await set_attributes(out)

        caption = get_string("audiotools_7").format(ss, dd)
        await e.client.send_file(
            e.chat_id,
            mmmm,
            thumb=ULTConfig.thumb,
            caption=caption,
            attributes=attributes,
            force_document=False,
            reply_to=e.reply_to_msg_id,
        )
        await xxx.delete()
    else:
        await e.eor(get_string("audiotools_1"), time=5)


@ultroid_cmd(pattern="extractaudio$")
async def ex_aud(e):
    reply = await e.get_reply_message()
    if not (reply and reply.media and mediainfo(reply.media).startswith("video")):
        return await e.eor(get_string("audiotools_8"))
    name = reply.file.name or "video.mp4"
    vfile = reply.media.document
    msg = await e.eor(get_string("com_1"))
    c_time = time.time()
    file = await downloader(
        f"resources/downloads/{name}",
        vfile,
        msg,
        c_time,
        f"Downloading {name}...",
    )

    out_file = f"{file.name}.aac"
    cmd = f"ffmpeg -i {file.name} -vn -acodec copy {out_file}"
    o, err = await bash(cmd)
    osremove(file.name)
    attributes = await set_attributes(out_file)

    f_time = time.time()
    try:
        fo = await uploader(out_file, out_file, f_time, msg, f"Uploading {out_file}...")

    except FileNotFoundError:
        return await eor(msg, get_string("audiotools_9"))
    await e.reply(
        get_string("audiotools_10"),
        file=fo,
        thumb=ULTConfig.thumb,
        attributes=attributes,
    )
    await msg.delete()
