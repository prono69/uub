# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available

• `{i}zip <reply to file>`
    zip the replied file
    To set password on zip: `{i}zip <password>` reply to file

• `{i}unzip <reply to zip file>`
    unzip the replied file.

• `{i}azip <reply to file>`
   add file to batch for batch upload zip

• `{i}dozip`
   upload batch zip the files u added from `{i}azip`
   To set Password: `{i}dozip <password>`

"""

import asyncio
import os
import time
from shlex import quote

from . import (
    HNDLR,
    ULTConfig,
    bash,
    check_filename,
    get_all_files,
    get_string,
    osremove,
    tg_downloader,
    ultroid_cmd,
)


@ultroid_cmd(pattern="zip( (.*)|$)")
async def zipp(event):
    reply = await event.get_reply_message()
    if not (reply and reply.media):
        return await event.eor(get_string("zip_1"))

    xx = await event.eor(get_string("com_1"))
    file, _ = await tg_downloader(media=reply, event=xx, show_progress=True)
    inp = check_filename(file.replace(file.split(".")[-1], "zip"))
    passw = event.pattern_match.group(2)
    if passw:
        await bash(f"zip -r --password {quote(passw)} {quote(inp)} {quote(file)}")
    else:
        await bash(f"zip -r {quote(inp)} {quote(file)}")

    xxx, _ = await event.client.fast_uploader(
        inp, show_progress=True, event=xx, save_cache=False
    )
    await reply.reply(
        f"`{xxx.name}`",
        file=xxx,
        force_document=True,
        thumb=ULTConfig.thumb,
    )
    osremove(file, inp)
    await xx.delete()


@ultroid_cmd(pattern="unzip( (.*)|$)")
async def unzipp(event):
    reply = await event.get_reply_message()
    file = event.pattern_match.group(2)
    if not ((reply and reply.media) or file):
        return await event.eor(get_string("zip_1"))

    xx = await event.eor(get_string("com_1"))
    if not file:
        if not getattr(reply.media, "document", None):
            return await xx.edit(get_string("zip_3"))
        if not reply.file.name.endswith(("zip", "rar", "exe")):
            return await xx.edit(get_string("zip_3"))
        file, _ = await tg_downloader(media=reply, event=xx, show_progress=True)
    if os.path.isdir("unzip"):
        await bash("rm -rf unzip")
    os.mkdir("unzip")
    await xx.edit("`Unzipping files...`")
    await bash(f"7z x {quote(file)} -aoa -o unzip")
    await asyncio.sleep(5)
    ok = get_all_files("unzip")
    for x in ok:
        xxx, _ = await event.client.fast_uploader(
            x, show_progress=True, event=xx, save_cache=False
        )
        await xx.respond(
            f"`{xxx.name}`",
            file=xxx,
            force_document=True,
            thumb=ULTConfig.thumb,
        )
    await bash("rm -rf unzip")
    await xx.delete()


@ultroid_cmd(pattern="addzip$")
async def azipp(event):
    reply = await event.get_reply_message()
    if not (reply and reply.media):
        return await event.eor(get_string("zip_1"))

    xx = await event.eor(get_string("com_1"))
    os.makedirs("zip", exist_ok=True)
    file, _ = await tg_downloader(media=reply, event=xx, show_progress=True)
    await xx.edit(
        f"Downloaded `{file}` succesfully\nNow Reply To Other Files To Add And Zip all at once",
    )


@ultroid_cmd(pattern="dozip( (.*)|$)")
async def do_zip(event):
    if not os.path.isdir("zip"):
        return await event.eor(get_string("zip_2").format(HNDLR))

    xx = await event.eor(get_string("com_1"))
    out = check_filename("ultroid.zip")
    if passw := event.pattern_match.group(2):
        await bash(f"zip -r --password {passw} {quote(out)} zip/*")
    else:
        await bash(f"zip -r {quote(out)} zip/*")

    xxx, _ = await event.client.fast_uploader(
        out, show_progress=True, event=xx, save_cache=True
    )
    await xx.respond(
        f"`{out}`",
        file=xxx,
        force_document=True,
        thumb=ULTConfig.thumb,
    )
    osremove("pdf", folders=True)
    await xx.delete()
