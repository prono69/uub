# Original Source : https://github.com/subinps/tglogging
# Modified to make compatible with Ultroid.
#
# first push : 24-09-2022, v0.7
#

import asyncio
from io import BytesIO
from copy import deepcopy
from random import randrange
from logging import StreamHandler
from aiohttp import ClientSession


# ----------------------------------------------------------------------------

loop = asyncio.get_event_loop()

_TG_API = "https://api.telegram.org/bot{}"
_TG_MSG_LIMIT = 4030
_PAYLOAD = {"disable_web_page_preview": True, "parse_mode": "Markdown"}
_MAX_LOG_LIMIT = 8192

# ----------------------------------------------------------------------------


class TGLogHandler(StreamHandler):
    def __init__(self, chat, token):
        self.chat = chat
        self.log_db = []
        self.current = ""
        self.active = False
        self.editCount = 0
        self.newmsgCount = 0
        self.triggerCount = 0
        self.message_id = None
        self.processedCount = 0
        self._floodwait = False
        self.__url = _TG_API.format(token)
        _PAYLOAD.update({"chat_id": chat})
        StreamHandler.__init__(self)

    def __str__(self):
        count = self.count
        active = self.active
        return f"Total Queued Items - {len(self.log_db)} | Active - {active} | Count - {count}"

    def emit(self, record):
        msg = self.format(record)
        self.log_db.append("\n\n\n" + msg)
        self.triggerCount += 1
        if not (self.active or self._floodwait):
            self.active = True
            loop.create_task(self.runQueue())

    async def runQueue(self):
        await asyncio.sleep(3)
        if not self.log_db:
            self.active = False
            return
        self.active = True
        cpy = deepcopy(self.log_db)
        await self.handle_logs(cpy)
        await self.runQueue()

    def splitter(self, logs):
        _log = []
        current = self.current
        for l in logs:
            edit_left = _TG_MSG_LIMIT - len(current)
            if edit_left > len(l):
                current += l
            else:
                _log.append(current)
                current = l
        _log.append(current)
        return _log

    async def conditionX(self, log_msg):
        lst = self.splitter(log_msg)
        if lst[0] != self.current:
            await self.edit_message(lst[0], sleep=5)
        for i in lst[1:]:
            await self.send_message(i, sleep=randrange(6, 15))

    async def handle_logs(self, db):
        edit_left = _TG_MSG_LIMIT - len(self.current)
        as_file = any(len(i) > _TG_MSG_LIMIT for i in db)
        if edit_left > len(db):
            msg = self.current + "".join(db)
            await self.edit_message(msg, sleep=randrange(4, 10))
        elif as_file or total_len > _MAX_LOG_LIMIT:
            await self.send_file("".join(db), sleep=randrange(8, 15))
        else:
            await self.conditionX(db)
        self.log_db = self.log_db[len(db) :]
        self.processedCount += 1

    async def send_request(self, url, payload):
        async with ClientSession() as session:
            async with session.request("POST", url, json=payload) as response:
                return await response.json()

    async def cancel_floodwait(self, sleep):
        await asyncio.sleep(sleep)
        self._floodwait = False

    async def send_message(self, message, sleep):
        payload = deepcopy(_PAYLOAD)
        payload["text"] = f"```{message}```"
        if ids := self.message_id:
            payload["reply_to_msg_id"] = ids
        res = await self.send_request(self.__url + "/sendMessage", payload)
        if res.get("ok"):
            self.message_id = int(res["result"]["message_id"])
            self.current = message
            self.newmsgCount += 1
            await asyncio.sleep(sleep)
        else:
            await self.handle_error(res)

    async def edit_message(self, message, sleep):
        if not self.message_id:
            await self.send_message(message, sleep)
            return
        payload = deepcopy(_PAYLOAD)
        payload.update({"message_id": self.message_id, "text": f"```{message}```"})
        res = await self.send_request(self.__url + "/editMessageText", payload)
        if res.get("ok"):
            self.editCount += 1
            self.current = message
            await asyncio.sleep(sleep)
        else:
            await self.handle_error(res)

    async def send_file(self, logs, sleep):
        file = BytesIO(logs.encode())
        file.name = "tglogging.txt"
        url = self.__url + "/sendDocument"
        payload = deepcopy(_PAYLOAD)
        payload["caption"] = "Too much logs to send, hence sending as file."
        if ids := self.message_id:
            payload["reply_to_msg_id"] = ids
        files = {"document": file}
        payload.pop("disable_web_page_preview", None)
        async with ClientSession() as session:
            async with session.request(
                "POST", url, params=payload, data=files
            ) as response:
                res = await response.json()
        if res.get("ok"):
            self.current = ""
            self.message_id = None
            await asyncio.sleep(sleep)
        else:
            await self.handle_error(res)

    async def handle_error(self, resp):
        error = resp.get("parameters", {})
        if not error:
            if (
                resp.get("error_code") == 401
                and resp.get("description") == "Unauthorized"
            ):
                return
            print(f"Errors while updating TG logs: {resp}")
            return
        elif s := error.get("retry_after"):
            self._floodwait = True  # error.get("retry_after")
            print(f"floodwait in tglogging: sleeping for {s}")
            sleep = s + (s // 3)
            asyncio.gather(cancel_floodwait(sleep))
