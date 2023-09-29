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

from pyUltroid.fns.tools import _stdr
from . import (
    LOGS,
    ULTConfig,
    bash,
    check_filename,
    genss,
    get_help,
    get_string,
    humanbytes,
    mediainfo,
    osremove,
    set_attributes,
    tg_downloader,
    time_formatter,
    ultroid_cmd,
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
    sec = e.pattern_match.group(2)
    if not sec or "-" not in sec:
        return await e.eor(get_string("audiotools_3"), time=5)
    a, b = sec.split("-")
    if int(a) >= int(b):
        return await e.eor(get_string("audiotools_4"), time=5)

    reply = await e.get_reply_message()
    if not (
        reply and reply.media and mediainfo(reply.media).startswith(("video", "audio"))
    ):
        return await e.eor(get_string("audiotools_1"), time=5)

    xxx = await e.eor(get_string("audiotools_5"))
    path, t_time = await tg_downloader(media=reply, event=xxx, show_progress=True)
    o_size = Path(path).stat().st_size
    diff = time_formatter(t_time * 1000)
    out = check_filename(Path(path).with_suffix(".aac"))
    if int(b) > int(await genss(path)):
        osremove(path)
        return await xxx.edit(get_string("audiotools_6"))

    ss, dd = _stdr(int(a)), _stdr(int(b))
    await xxx.edit(
        f"Downloaded `{path}` of `{humanbytes(o_size)}` in `{diff}`.\n\nNow Trimming Audio from `{ss}` to `{dd}`..."
    )
    await asyncio.sleep(2)
    cmd = f"ffmpeg -i {quote(path)} -preset ultrafast -ss {ss} -to {dd} -vn -acodec copy {quote(out)} -y"
    await bash(cmd)
    attributes = await set_attributes(out)
    mmmm, _ = await e.client.fast_uploader(
        out, show_progress=True, event=xxx, save_cache=False
    )
    caption = get_string("audiotools_7").format(ss, dd)
    await reply.reply(
        caption,
        file=mmmm,
        thumb=ULTConfig.thumb,
        attributes=attributes,
        force_document=False,
    )
    osremove(out, path)
    await xxx.delete()


@ultroid_cmd(pattern="extractaudio$")
async def ex_aud(e):
    reply = await e.get_reply_message()
    if not (reply and reply.media and mediainfo(reply.media).startswith("video")):
        return await e.eor(get_string("audiotools_8"))

    msg = await e.eor(get_string("com_1"))
    path, _ = await tg_downloader(media=reply, event=msg, show_progress=True)
    out_file = Path(path).with_suffix(".aac")
    cmd = f"ffmpeg -i {quote(path)} -vn -acodec copy {out_file}"
    await bash(cmd)
    if not Path(out_file).is_file():
        return await msg.edit(get_string("audiotools_9"))

    attributes = await set_attributes(out_file)
    mmmm, _ = await e.client.fast_uploader(
        out_file, show_progress=True, event=msg, save_cache=False
    )
    await reply.reply(
        get_string("audiotools_10"),
        file=mmmm,
        thumb=ULTConfig.thumb,
        attributes=attributes,
    )
    osremove(out_file, path)
    await msg.delete()
