import asyncio
from os import remove, path

from telethon.utils import get_display_name as title_
from telethon.errors import FloodWaitError

from .. import LOGS, udB, ultroid_bot as ultroid


# ~~~~~~~~~~~~~~ KEYS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

KEYS = udB.get_key("FRWD_DB")
CAPTION_ = "#AutoPost  «{0}»  [{1}]({2})\n{3}"
to_fwd = udB.get_key("TO_FWD")

# ~~~~~~~~~~~~~~ Main FWD ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def main_fwd():
    if udB.get_key("_RESTART"):
        return LOGS.warning("Found 'RESTART' key! Skipping forwards.")
    if udB.get_key("STOP_FORWARDS"):
        return LOGS.info("not forwarding anything ...")
    LOGS.info("Starting Forwards.")
    fin = {}
    for k, v in KEYS.items():
        try:
            ent = await ultroid.get_entity(k)
            _title = _getname(fin, title_(ent))
            await asyncio.sleep(1.75)
            fin[_title] = 0
        except Exception as ex:
            LOGS.exception(f"Channel '{k}' died!")
        else:
            if x := await iterr(ent, v[1]):
                fwdb(k, max(x))
                fin[_title] = len(x)

    # empty_chats = list(k for k, v in fin.items() if bool(v))
    # LOGS.debug("Empty Chats: " + " | ".join(empty_chats))

    from .tools import json_parser

    LOGS.debug(json_parser(fin, indent=1))
    LOGS.info(
        f"Forwarded {sum(fin.values())} files from {len(list(filter(bool, fin.values())))} Chats."
    )


def _getname(dct, name):
    n = 1
    while name in dct:
        name += "_v" + str(n)
        n += 1
    return name


# ~~~~~~~~~~~~~~ DB Handler ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def fwdb(chat_, id_):
    a = udB.get_key("FRWD_DB")
    a[chat_][1] = id_
    udB.set_key("FRWD_DB", a)


# ~~~~~~~~~~~~~~ Iterator ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def iterr(chat, id):
    def slp_time(t):
        if not t:
            return 0.01
        elif t < 12:
            return 0.5
        elif t < 36:
            return 1.15
        return 1.75 if t < 80 else 2.75

    albm = {}
    IDS = []
    types = ("photo", "document", "video", "gif")
    async for x in ultroid.iter_messages(
        chat.id,
        reverse=True,
        min_id=id,
    ):
        if not x.media or not any(getattr(x.media, i, None) for i in types):
            continue

        # Tmp DB
        IDS.append(x.id)

        # Album
        if x.grouped_id:
            if albm.get(x.grouped_id):
                albm[x.grouped_id].append(x)
            else:
                albm[x.grouped_id] = [x]
            continue

        _ = await fx_photo(x) if KEYS[x.chat_id][0] == "pic" else await fx_video(x)
        await asyncio.sleep(slp_time(len(IDS)))

    # Album
    if albm:
        await fx_album(albm)
        albm.clear()

    if IDS:
        LOGS.debug(f"Forwarded {len(IDS)} from {title_(chat)}")
        return IDS


# ~~~~~~~~~~~~~~ Sender ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def fx_send(file, cap, title="Not Given"):
    if not file:
        return
    try:
        snd = await ultroid.send_file(
            to_fwd,
            file,
            caption=cap,
            force_document=False,
            silent=True,
        )
    except FloodWaitError as fx:
        LOGS.exception(f"Sleeping for {fx.seconds} || {title}")
        await asyncio.sleep(fx.seconds + 20)
        await ultroid.send_file(to_fwd, file, caption=cap[:1023])
    except Exception as ex:
        LOGS.exception(f"Unhandeled Exception • fx_send • {ex} • {title}")
    else:
        if file and path.exists(str(file)):
            remove(file)
        if type(file) != list and snd.gif:
            from .helper import cleargif

            await cleargif(snd)


# ~~~~~~~~~~~~~~ Album Handler ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def fx_album(dct):
    for _, o in dct.items():
        cap = CAPTION_.format("³", title_(o[0].chat), o[0].message_link, o[0].text)
        await fx_send(o, cap, title_(o[0].chat))
        await asyncio.sleep(2)


# ~~~~~~~~~~~~~~ Photo ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def fx_photo(args):
    cap = CAPTION_.format("¹", title_(args.chat), args.message_link, args.text or "")
    if args.sticker:
        return
    elif args.photo:
        pic = args.media
    elif args.file.mime_type.split("/")[0] == "image":
        if args.file.size > 10 * 1024 * 1024:
            return
        pic = await ultroid.download_media(args)
    else:
        return
    await fx_send(pic, cap, title_(args.chat))


# ~~~~~~~~~~~~~~ Video ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def fx_video(args):
    cap = CAPTION_.format("²", title_(args.chat), args.message_link, args.text or "")
    if args.sticker:
        return
    elif args.photo or args.video or args.gif:
        vid = args.media
    elif args.file.mime_type.split("/")[0] == "video":
        vid = args.media
    elif args.file.mime_type.split("/")[0] == "image":
        if args.file.size > 5 * 1024 * 1024:
            return
        vid = await ultroid.download_media(args)
    else:
        return
    await fx_send(vid, cap, title_(args.chat))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
