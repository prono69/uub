import asyncio
from os import remove, path
from random import randrange

from telethon.utils import get_display_name as chatTitle
from telethon.errors import FloodWaitError

from .helper import cleargif
from .. import asst, LOGS, udB, ultroid_bot as ultroid


class forwarder:
    def __init__(self):
        self.DB = {}
        self.count = 0
        self.working = False
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
        if type(gif) != list and gif.gif:
            await cleargif(gif)

    @staticmethod
    def updatedb(chat, _new):
        x = udB.get_key("FRWD_DB")
        if _new > x[chat][1]:
            x[chat][1] = _new
            udB.set_key("FRWD_DB", x)

    def __str__(self):
        count = self.count
        active = self.working
        return f"Total Items in Queue - {len(self.DB)} | Working - {active} | Count - {count}"

    async def __call__(self, fr=False):
        if fr:
            await self.catchup()

    async def addQueue(self, *args, callfunc=True):
        self.count += 1
        self.DB[self.count] = args
        if callfunc and not self.working:
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
        await asyncio.sleep(randrange(8, 16))

    async def mainQueue(self):
        if not (DB := self.DB):
            self.working = False
            return
        self.working = True
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
            chat = self._getname(fin, chatTitle(ent))
            await asyncio.sleep(2)
            if fwd := await self.iter_chat(ent.chat_id, v[1]):
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

    async def main(self, file, caption):
        try:
            cpy = await ultroid.send_file(self._DESTINATION, file, caption=caption)
            await self._cleargif(cpy)
            if type(file) is str and path.isfile(file):
                remove(file)
        except Exception:
            link = (
                None
                if type(file) is str
                else (file[0].message_link if type(file) is list else file.message_link)
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
            await self.album_handler(album, callfunc=False)
        return msg_ids

    async def album_handler(self, data, callfunc):
        for album in data.values():
            caption = self._CAPTION.format(
                "³",
                chatTitle(album[0].chat),
                album[0].message_link,
                album[0].text,
            )
            await self.addQueue(i, caption[:1023], callfunc=callfunc)

    async def media_handler(self, file, callfunc=False):
        media = None
        if file.sticker:
            return
        if file.photo:
            media = file
        elif (
            file.file.mime_type.split("/")[0] == "image"
            and file.file.size < 10 * 1024 * 1024
        ):
            media = await file.download_media("resources/downloads/")
        elif self._KEYS[file.chat_id][0] == "vid":
            if file.video or file.gif or file.file.mime_type.split("/")[0] == "video":
                media = file
        if media:
            caption = self._CAPTION.format(
                "²", chatTitle(file.chat), file.message_link, file.text or ""
            )
            await self.addQueue(
                media,
                caption[:1023],
                callfunc=callfunc,
            )


fwdx = forwarder()
