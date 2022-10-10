# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
• `{i}getmsg <message link>`
  Get messages from chats with forward/copy restrictions.
"""

import os

from telethon.errors.rpcerrorlist import ChatForwardsRestrictedError

from pyUltroid.fns.tools import get_chat_and_msgid

from . import LOGS, eor, get_string, ultroid_cmd


@ultroid_cmd(
    pattern="getmsg( ?(.*)|$)",
    fullsudo=True,
)
async def get_restriced_msg(event):
    match = event.pattern_match.group(1).strip()
    if not match:
        await event.eor("`Please provide a link!`", time=5)
        return
    xx = await event.eor(get_string("com_1"))
    chat, msg = get_chat_and_msgid(match)
    if not (chat and msg):
        return await event.eor(
            f"{get_string('gms_1')}!\nEg: `https://t.me/TeamUltroid/3 or `https://t.me/c/1313492028/3`"
        )
    try:
        message = await event.client.get_messages(chat, ids=msg)
    except Exception as er:
        return await event.eor(f"**ERROR**\n`{er}`")
    try:
        await event.client.send_message(event.chat_id, message)
        await xx.try_delete()
        return
    except ChatForwardsRestrictedError:
        pass
    if message.media:
        thumb = None
        if doc := message.document:
            attributes = doc.attributes
            if doc.thumbs:
                thumb = await message.download_media(thumb=-1)
            media, _ = await event.client.fast_downloader(
                doc,
                show_progress=True,
                event=xx,
                message=f"Downloading {message.file.name}...",
            )
            media = media.name
        else:
            attributes = []
            media = await message.download_media("resources/downloads/")
        await xx.edit("`Uploading...`")
        uploaded, _ = await event.client.fast_uploader(
            media, event=xx, show_progress=True, to_delete=True
        )
        typ = not bool(message.video)
        await event.reply(
            message.text,
            file=uploaded,
            supports_streaming=typ,
            force_document=typ,
            thumb=thumb,
            attributes=attributes,
        )
        await xx.delete()
        if thumb:
            os.remove(thumb)
