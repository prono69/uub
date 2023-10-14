# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("help_admintools")

import asyncio

from telethon.errors import BadRequestError
from telethon.errors.rpcerrorlist import ChatNotModifiedError, UserIdInvalidError
from telethon.tl.functions.channels import EditAdminRequest, GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest, SetHistoryTTLRequest
from telethon.tl.types import InputMessagesFilterPinned
from telethon.utils import get_display_name

from pyUltroid.dB import DEVLIST
from pyUltroid.fns.admins import ban_time
from pyUltroid.fns.info import get_uinfo

from . import HNDLR, LOGS, eod, eor, get_string, inline_mention, types, ultroid_cmd


@ultroid_cmd(
    pattern="promote( (.*)|$)",
    admins_only=True,
    manager=True,
    require="add_admins",
    fullsudo=True,
)
async def prmte(ult):
    xx = await ult.eor(get_string("com_1"))
    user, rank = await get_uinfo(ult)
    rank = rank or "Admin"
    FullRight = False
    if not user:
        return await xx.edit(get_string("pro_1"))
    if rank.split()[0] == "-f":
        try:
            rank = rank.split(maxsplit=1)[1]
        except IndexError:
            rank = "Admin"
        FullRight = True
    try:
        if FullRight:
            await ult.client(
                EditAdminRequest(ult.chat_id, user.id, ult.chat.admin_rights, rank)
            )
        else:
            await ult.client.edit_admin(
                ult.chat_id,
                user.id,
                invite_users=True,
                ban_users=True,
                delete_messages=True,
                pin_messages=True,
                manage_call=True,
                title=rank,
            )
        await eod(
            xx, get_string("pro_2").format(inline_mention(user), ult.chat.title, rank)
        )
    except Exception as ex:
        return await xx.edit(f"`{ex}`")


@ultroid_cmd(
    pattern="demote( (.*)|$)",
    admins_only=True,
    manager=True,
    require="add_admins",
    fullsudo=True,
)
async def dmote(ult):
    xx = await ult.eor(get_string("com_1"))
    user, rank = await get_uinfo(ult)
    if not rank:
        rank = "Not Admin"
    if not user:
        return await xx.edit(get_string("de_1"))
    try:
        await ult.client.edit_admin(
            ult.chat_id,
            user.id,
            invite_users=None,
            ban_users=None,
            delete_messages=None,
            pin_messages=None,
            manage_call=None,
            title=rank,
        )
        await eod(xx, get_string("de_2").format(inline_mention(user), ult.chat.title))
    except Exception as ex:
        return await xx.edit(f"`{ex}`")


@ultroid_cmd(
    pattern="ban( (.*)|$)",
    admins_only=True,
    manager=True,
    require="ban_users",
    fullsudo=True,
)
async def bban(ult):
    something = await get_uinfo(ult)
    if not something:
        return
    user, reason = something
    if not user:
        return await eod(ult, get_string("ban_1"))
    if user.id in DEVLIST:
        return await eod(ult, get_string("ban_2"))
    try:
        await ult.client.edit_permissions(ult.chat_id, user.id, view_messages=False)
    except UserIdInvalidError:
        return await eod(ult, get_string("adm_1"))
    except BadRequestError:
        return await eod(ult, get_string("ban_3"))
    senderme = inline_mention(await ult.get_sender())
    userme = inline_mention(user)
    text = get_string("ban_4").format(userme, senderme, ult.chat.title)
    if reason:
        text += get_string("ban_5").format(reason)
    await eod(ult, text)


@ultroid_cmd(
    pattern="unban( (.*)|$)",
    admins_only=True,
    manager=True,
    require="ban_users",
    fullsudo=True,
)
async def uunban(ult):
    xx = await ult.eor(get_string("com_1"))
    if ult.text[1:].startswith("unbanall"):
        return
    something = await get_uinfo(ult)
    if not something:
        return
    user, reason = something
    if not user:
        return await xx.edit(get_string("unban_1"))
    try:
        await ult.client.edit_permissions(ult.chat_id, user.id, view_messages=True)
    except UserIdInvalidError:
        return await eod(ult, get_string("adm_1"))
    except BadRequestError:
        return await xx.edit(get_string("adm_2"))
    sender = inline_mention(await ult.get_sender())
    text = get_string("unban_3").format(inline_mention(user), sender, ult.chat.title)
    if reason:
        text += get_string("ban_5").format(reason)
    await xx.edit(text)


@ultroid_cmd(
    pattern="kick( (.*)|$)",
    manager=True,
    require="ban_users",
    fullsudo=True,
)
async def kck(ult):
    if "kickme" in ult.text:
        return
    if ult.is_private:
        return await ult.eor("`Use this in Group/Channel.`", time=5)
    ml = ult.text.split(" ", maxsplit=1)[0]
    xx = await ult.eor(get_string("com_1"))
    something = await get_uinfo(ult)
    if not something:
        return
    user, reason = something
    if not user:
        return await xx.edit(get_string("adm_1"))
    if user.id in DEVLIST:
        return await xx.edit(get_string("kick_2"))
    if getattr(user, "is_self", False):
        return await xx.edit(get_string("kick_3"))
    try:
        await ult.client.kick_participant(ult.chat_id, user.id)
    except BadRequestError as er:
        LOGS.info(er)
        return await xx.edit(get_string("kick_1"))
    except Exception as e:
        LOGS.exception(e)
        return
    text = get_string("kick_4").format(
        inline_mention(user), inline_mention(await ult.get_sender()), ult.chat.title
    )
    if reason:
        text += get_string("ban_5").format(reason)
    await xx.edit(text)


@ultroid_cmd(
    pattern="tban( (.*)|$)",
    admins_only=True,
    manager=True,
    require="ban_users",
    fullsudo=True,
)
async def tkicki(e):
    huh = e.text.split()
    inputt = None
    try:
        tme = huh[1]
    except IndexError:
        return await e.eor(get_string("adm_3"), time=15)
    try:
        inputt = huh[2]
    except IndexError:
        if e.reply_to_msg_id:
            inputt = (await e.get_reply_message()).sender_id
    if not inputt:
        return await e.eor(get_string("tban_1"))
    userid = await e.client.parse_id(inputt)
    try:
        user = await e.client.get_entity(userid)
    except Exception as ex:
        return await eor(e, f"`{ex}`")
    try:
        bun = ban_time(tme)
        await e.client.edit_permissions(
            e.chat_id, user.id, until_date=bun, view_messages=False
        )
        await eod(
            e,
            get_string("tban_2").format(inline_mention(user), e.chat.title, tme),
            time=15,
        )
    except Exception as m:
        return await e.eor(str(m))


@ultroid_cmd(pattern="pin$", manager=True, require="pin_messages", fullsudo=True)
async def pin(msg):
    if not msg.is_reply:
        return await eor(msg, get_string("pin_1"))
    me = await msg.get_reply_message()
    if me.is_private:
        text = "`Pinned.`"
    else:
        text = f"Pinned [This Message]({me.message_link}) !"
    try:
        await msg.client.pin_message(msg.chat_id, me.id, notify=False)
    except BadRequestError:
        return await eor(msg, get_string("adm_2"))
    except Exception as e:
        return await eor(msg, f"**ERROR:**`{e}`")
    await eor(msg, text)


@ultroid_cmd(
    pattern="unpin($| (.*))",
    manager=True,
    require="pin_messages",
    fullsudo=True,
)
async def unp(ult):
    xx = await ult.eor(get_string("com_1"))
    ch = (ult.pattern_match.group(1).strip()).strip()
    msg = None
    if ult.is_reply:
        msg = ult.reply_to_msg_id
    elif ch != "all":
        return await xx.edit(get_string("unpin_1").format(HNDLR))
    try:
        await ult.client.unpin_message(ult.chat_id, msg)
    except BadRequestError:
        return await xx.edit(get_string("adm_2"))
    except Exception as e:
        return await xx.edit(f"**ERROR:**`{e}`")
    await xx.edit("`Unpinned!`")


@ultroid_cmd(
    pattern="tpin( (.*)|$)",
    admins_only=True,
    manager=True,
    require="pin_messages",
    fullsudo=True,
)
async def pin_message(ult):
    match = ult.pattern_match.group(1).strip()
    if not ult.is_reply:
        return await ult.eor("`Reply to message..`", time=6)
    if not match:
        return await ult.eor("`Please provide time..`", time=8)
    msg = await ult.eor(get_string("com_1"))
    msg_id = ult.reply_to_msg_id
    try:
        time = ban_time(match)
        await ult.client.pin_message(ult.chat_id, msg_id)
        await msg.eor(f"`pinned for time` `{time}`", time=8)
    except Exception as er:
        return await msg.edit(str(er))
    await asyncio.sleep(time)
    try:
        await ult.client.unpin_message(ult.chat_id, msg_id)
    except Exception as er:
        LOGS.exception(er)


@ultroid_cmd(pattern="purge( (\d*)|$)", manager=True, require="delete_messages")
async def fastpurger(purg):
    match = purg.pattern_match.group(2)
    match = int(match) if match else None
    reply_id = purg.reply_to_msg_id
    if not (match or reply_id):
        return await eor(purg, get_string("purge_1"), time=5)

    if not purg._client._bot and (purg.is_private or isinstance(purg.chat, types.Chat)):
        p = 0
        async for msg in purg.client.iter_messages(
            purg.chat_id,
            limit=match,
            max_id=purg.id,
            min_id=0 if match else reply_id - 1,
        ):
            try:
                await msg.delete()
                p += 1
            except Exception:
                pass
        await purg.eor(f"__Purged {p} Messages!__", time=5)
        return

    from_id = reply_id or purg.id - match
    purge_range = list(range(from_id, purg.id))
    try:
        await purg.client.delete_messages(purg.chat_id, purge_range)
    except Exception as er:
        LOGS.exception(er)
    await purg.eor("__Fast purge complete!__", time=5)


@ultroid_cmd(
    pattern="purgeme( (\d*)|$)",
)
async def fastpurgeme(purg):
    num = purg.pattern_match.group(2)
    num = int(num) if num else None
    if not (num or purg.reply_to):
        return await purg.eor(
            "__Reply to a message to Purge from or use it like__ `.purgeme <num>`", time=10,
        )

    count = 0
    async for msg in purg.client.iter_messages(
        purg.chat_id,
        limit=num,
        from_user="me",
        max_id=purg.id,
        min_id=0 if num else purg.reply_to_msg_id - 1,
    ):
        try:
            await msg.delete()
            count += 1
        except Exception:
            pass

    return await purg.eor(f"__Purged {count} Messages!__", time=5)


@ultroid_cmd(
    pattern="purgeall$",
)
async def _(e):
    if not e.is_reply:
        return await eod(
            e,
            get_string("purgeall_1"),
        )

    msg = await e.get_reply_message()
    name = msg.sender
    try:
        await e.client.delete_messages(e.chat_id, from_user=msg.sender_id)
        await e.eor(get_string("purgeall_2").format(name.first_name), time=5)
    except Exception as er:
        return await e.eor(str(er), time=5)


@ultroid_cmd(pattern="pinned$", manager=True, groups_only=True)
async def djshsh(event):
    chat = await event.get_chat()
    if isinstance(chat, types.Chat):
        FChat = await event.client(GetFullChatRequest(chat.id))
    elif isinstance(chat, types.Channel):
        FChat = await event.client(GetFullChannelRequest(chat.id))
    else:
        return
    msg_id = FChat.full_chat.pinned_msg_id
    if not msg_id:
        return await event.eor(get_string("pinned_1"))
    msg = await event.client.get_messages(chat.id, ids=msg_id)
    if msg:
        await event.eor(get_string("pinned_2").format(msg.message_link))


@ultroid_cmd(
    pattern="listpinned$",
)
async def get_all_pinned(event):
    x = await event.eor(get_string("com_1"))
    chat_id = (str(event.chat_id)).replace("-100", "")
    chat_name = get_display_name(event.chat)
    a = ""
    c = 1
    async for i in event.client.iter_messages(
        event.chat_id, filter=InputMessagesFilterPinned
    ):
        if i.message:
            t = " ".join(i.message.split()[:4])
            txt = f"{t}...."
        else:
            txt = "Go to message."
        a += f"{c}. <a href=https://t.me/c/{chat_id}/{i.id}>{txt}</a>\n"
        c += 1

    if c == 1:
        m = f"<b>The pinned message in {chat_name}:</b>\n\n"
    else:
        m = f"<b>List of pinned message(s) in {chat_name}:</b>\n\n"

    if not a:
        return await eor(x, get_string("listpin_1"), time=5)

    await x.edit(m + a, parse_mode="html")


@ultroid_cmd(
    pattern="autodelete( (.*)|$)",
    admins_only=True,
)
async def autodelte(ult):
    match = ult.pattern_match.group(1).strip()
    if not match or match not in ["24h", "7d", "1m", "off"]:
        return await ult.eor("`Please Use in Proper Format..`", time=5)
    if match == "24h":
        tt = 3600 * 24
    elif match == "7d":
        tt = 3600 * 24 * 7
    elif match == "1m":
        tt = 3600 * 24 * 31
    else:
        tt = 0
    try:
        await ult.client(SetHistoryTTLRequest(ult.chat_id, period=tt))
    except ChatNotModifiedError:
        return await ult.eor(
            f"Auto Delete Setting is Already same to `{match}`", time=5
        )
    await ult.eor(f"Auto Delete Status Changed to `{match}` !")
