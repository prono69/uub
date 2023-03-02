# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

from asyncio import sleep

from telethon.errors import MessageDeleteForbiddenError, MessageNotModifiedError
from telethon.tl.custom import Message
from telethon.tl.types import MessageService


# edit or reply
async def eor(event, text=None, time=None, link_preview=False, edit_time=None, **args):
    reply_to = event.reply_to_msg_id or event
    if event.out and not isinstance(event, MessageService):
        if edit_time:
            await sleep(edit_time)
        if args.get("file") and not event.media:
            await event.delete()
            ok = await event.client.send_message(
                event.chat_id,
                text,
                link_preview=link_preview,
                reply_to=reply_to,
                **args
            )
        else:
            try:
                ok = await event.edit(text, link_preview=link_preview, **args)
            except MessageNotModifiedError:
                ok = event
    else:
        ok = await event.client.send_message(
            event.chat_id, text, link_preview=link_preview, reply_to=reply_to, **args
        )

    if time:
        await sleep(time)
        return await ok.delete()
    return ok


# edit or delete
async def eod(event, text=None, **kwargs):
    kwargs["time"] = kwargs.get("time", 8)
    return await eor(event, text, **kwargs)


# try delete
async def _try_delete(event):
    try:
        return await event.delete()
    except (MessageDeleteForbiddenError):
        pass
    except BaseException as er:
        from . import LOGS

        LOGS.error("Error while Deleting Message..")
        LOGS.exception(er)


# copy message
async def copy_message(msg, to_chat, **kwargs):
    if not isinstance(msg, Message) or isinstance(msg, MessageService):
        raise TypeError("Error: Invalid message type")

    try:
        if "caption" in kwargs:
            msg.text = kwargs.pop("caption")
        return await msg.client.send_message(to_chat, msg, **kwargs)
    except Exception:
        raise


setattr(Message, "eor", eor)
setattr(Message, "try_delete", _try_delete)
setattr(Message, "copy", copy_message)
