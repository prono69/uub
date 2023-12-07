# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}addsnip <word><reply to a message>`
    add the used word as snip relating to replied message.

• `{i}remsnip <word>`
    Remove the snip word..

• `{i}listsnip`
    list all snips.

• Use :
    type `$(ur snip word)` get setted reply.
"""

import os

from telegraph import upload_file as uf
from telethon.utils import pack_bot_file_id

from pyUltroid._misc import sudoers
from pyUltroid.dB.snips_db import add_snip, get_snips, list_snip, rem_snip
from pyUltroid.fns.tools import create_tl_btn, format_btn, get_msg_button

from . import events, get_string, mediainfo, not_so_fast, udB, ultroid_bot, ultroid_cmd
from ._inline import something


_SNIP_PREFIX = "$"


async def add_snips(e):
    if k := get_snips(e.text.lstrip(_SNIP_PREFIX)):
        msg = k["msg"]
        media = k["media"]
        rep = await e.get_reply_message()
        if rep:
            if k.get("button"):
                btn = create_tl_btn(k["button"])
                return await something(rep, msg, media, btn)
            await not_so_fast(rep.reply, msg, file=media)
        else:
            if k.get("button"):
                btn = create_tl_btn(k["button"])
                return await something(e, msg, media, btn, reply=None)
            await not_so_fast(e.respond, msg, file=media)
        if e.out:
            await e.try_delete()


@ultroid_cmd(pattern="addsnip( (.*)|$)")
async def touchsnip(e):
    wrd = e.pattern_match.group(2)
    wt = await e.get_reply_message()
    if not (wt and wrd):
        return await e.eor(get_string("snip_1"))
    wrd = wrd.lower().lstrip(_SNIP_PREFIX)
    btn = format_btn(wt.buttons) if wt.buttons else None
    if wt and wt.media:
        wut = mediainfo(wt.media)
        if wut.startswith(("pic", "gif")):
            dl = await wt.download_media()
            variable = uf(dl)
            os.remove(dl)
            m = f"https://graph.org{variable[0]}"
        elif wut == "video":
            if wt.media.document.size > 8 * 1000 * 1000:
                return await e.eor(get_string("com_4"), time=5)
            dl = await wt.download_media()
            variable = uf(dl)
            os.remove(dl)
            m = f"https://graph.org{variable[0]}"
        else:
            m = pack_bot_file_id(wt.media)
        if wt.text:
            txt = wt.text
            if not btn:
                txt, btn = get_msg_button(wt.text)
            add_snip(wrd, txt, m, btn)
        else:
            add_snip(wrd, None, m, btn)
    else:
        txt = wt.text
        if not btn:
            txt, btn = get_msg_button(wt.text)
        add_snip(wrd, txt, None, btn)
    await e.eor(f"Done: snip `${wrd}` Saved.")
    for func, _ in ultroid_bot.list_event_handlers():
        if func == add_snips:
            return
    func = lambda e: (
        (e.text and e.text.startswith(_SNIP_PREFIX))
        and not e.media
        and (e.out or e.sender_id in sudoers())
    )
    ultroid_bot.add_handler(add_snips, events.NewMessage(func=func))


@ultroid_cmd(pattern="remsnip( (.*)|$)")
async def rmsnip(e):
    wrd = e.pattern_match.group(2)
    if not wrd:
        return await e.eor(get_string("snip_2"))
    wrd = wrd.lower().lstrip(_SNIP_PREFIX)
    rem_snip(wrd)
    await e.eor(f"Done : snip `${wrd}` Removed.")


@ultroid_cmd(pattern="listsnip$")
async def lssnips(e):
    if x := list_snip():
        sd = "SNIPS Found :\n\n"
        return await e.eor(sd + x)
    await e.eor("No Snips Found in Database..")


if udB.get_key("SNIP"):
    func = lambda e: (
        (e.text and e.text.startswith(_SNIP_PREFIX))
        and not e.media
        and (e.out or e.sender_id in sudoers())
    )
    ultroid_bot.add_handler(add_snips, events.NewMessage(func=func))
