import asyncio
from os import remove, path
from random import randrange

from telethon.utils import get_peer_id, get_display_name as chatTitle
from telethon.errors import FloodWaitError

from .helper import cleargif
from .. import asst, LOGS, udB, ultroid_bot as ultroid


class forwarder:
    def __init__(self):
        self.DB = {}
        self.count = 0
        self.active = False
        self.working = self.active
        self._KEYS = udB.get_key("FRWD_DB")
        self._DESTINATION = udB.get_key("TO_FWD")
        self._CAPTION = "#AutoPost  «{0}»  [{1}]({2})\n{3}"

    @staticmethod
    def _getname(dct, title):
        n = 1
        while title in dct:
            title += "_v" + str(n)
            n += 1
        return title

    @staticmethod
    async def _cleargif(gif):
        if gif.client._bot:
            return
        elif type(gif) != list and gif.gif:
            await cleargif(gif)

    @staticmethod
    def updatedb(chat, _new):
        x = udB.get_key("FRWD_DB")
        if _new > x[chat][1]:
            x[chat][1] = _new
            udB.set_key("FRWD_DB", x)

    def __str__(self):
        count = self.count
        active = self.active
        return f"Total Items in Queue - {len(self.DB)} | Active - {active} | Count - {count}"

    async def __call__(self, fr=False):
        if fr:
            await self.catchup()

    async def addQueue(self, *args, callfunc=True):
        self.count += 1
        self.DB[self.count] = args
        if callfunc and not self.active:
            await self.mainQueue()

    def popQueue(self, key=None):
        if not key:
            try:
                key = next(iter(self.DB))
            except StopIteration:
                return
        self.DB.pop(key, None)

    async def runQueue(self, args):
        await self.main(*args)
        await asyncio.sleep(randrange(8, 17))

    async def mainQueue(self):
        if not (DB := self.DB):
            self.active = False
            return
        self.active = True
        key = next(iter(DB))
        await self.runQueue(DB.get(key))
        self.popQueue(key)
        await self.mainQueue()

    async def catchup(self):
        if udB.get_key("_RESTART"):
            return LOGS.warning("Found 'RESTART' key! Skipping forwards.")
        if udB.get_key("STOP_FORWARDS"):
            return LOGS.info("not forwarding anything ...")

        LOGS.info("Starting Forwards...")
        stat = {}
        for k, v in self._KEYS.items():
            try:
                ent = await ultroid.get_entity(k)
            except Exception as ex:
                LOGS.exception(f"Channel '{k}' died!")
                continue
            chat = self._getname(stat, chatTitle(ent))
            await asyncio.sleep(2)
            if fwd := await self.iter_chat(get_peer_id(ent), v[1]):
                self.updatedb(k, max(fwd))
                stat[chat] = len(fwd)
                LOGS.debug(f"Queued {len(fwd)} files from {chat}")
        if stat:
            asyncio.gather(self.init_queue(stat))

    async def init_queue(self, dct):
        from .tools import json_parser

        await asyncio.sleep(1)
        await self.mainQueue()
        LOGS.debug(json_parser(dct, indent=1))
        LOGS.info(
            f"Forwarded {sum(dct.values())} files from {len(list(filter(bool, dct.values())))} Chats!"
        )

    async def main(self, file, caption, is_path):
        album = True if type(file) is list else False
        try:
            media = (
                list(filter(bool, [i.media for i in file]))
                if album
                else (file if is_path else file.media)
            )
            cpy = await file.client.send_file(self._DESTINATION, media, caption=caption)
            await self._cleargif(cpy)
            if is_path:
                remove(file)
        except Exception:
            link = (
                file[0].message_link
                if album
                else (file if is_path else file.message_link)
            )
            LOGS.exception(f"Unhandeled Exception, main fwd: {link}")

    async def iter_chat(self, chat_id, min_id):
        album, msg_ids = {}, []
        _types = ("photo", "document", "video", "gif")
        async for x in ultroid.iter_messages(chat_id, reverse=True, min_id=min_id):
            if not (x.media and any(getattr(x.media, i, None) for i in _types)):
                continue
            msg_ids.append(x.id)
            if gid := x.grouped_id:
                if gid in album:
                    album[gid].append(x)
                else:
                    album[gid] = [x]
                continue
            await self.media_handler(x, callfunc=False)
        if album:
            for i in album.values():
                await self.album_handler(i, callfunc=False)
        return msg_ids

    async def album_handler(self, album, callfunc=False):
        is_path = False
        caption = self._CAPTION.format(
            "³",
            chatTitle(album[0].chat),
            album[0].message_link,
            album[0].text,
        )
        await self.addQueue(album, caption[:1023], is_path, callfunc=callfunc)

    async def media_handler(self, file, callfunc=False):
        media, is_path = None, False
        if file.sticker:
            return
        if file.photo:
            media = file
        elif (
            file.file.mime_type.split("/")[0] == "image"
            and file.file.size < 10 * 1024 * 1024
        ):
            media = await file.download_media("resources/downloads/")
            is_path = True
        elif self._KEYS[file.chat_id][0] == "vid":
            if file.video or file.gif or file.file.mime_type.split("/")[0] == "video":
                media = file
        if media:
            caption = self._CAPTION.format(
                "²", chatTitle(file.chat), file.message_link, file.text or ""
            )
            if not is_path:
                if rndx := await self.via_asst(file):
                    media = rndx
            await self.addQueue(
                media,
                caption[:1023],
                is_path,
                callfunc=callfunc,
            )

    async def via_asst(self, file):
        if n := file.chat.username:
            if randrange(100) > 50:
                if m := await asst.get_messages(n, ids=file.id):
                    return m


fwdx = forwarder()
