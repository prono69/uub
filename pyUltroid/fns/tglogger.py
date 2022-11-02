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

__DO_NOT_ACCESS__ = []
_TG_API = "https://api.telegram.org/bot{}"
_TG_MSG_LIMIT = 4020
_PAYLOAD = {"disable_web_page_preview": True, "parse_mode": "Markdown"}
_MAX_LOG_LIMIT = 12000

# ----------------------------------------------------------------------------

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ----------------------------------------------------------------------------


class TGLogHandler(StreamHandler):
    def __init__(self, chat, token):
        self.chat = chat
        self.log_db = []
        self.current = ""
        self.active = False
        self.editCount = 0
        self.triggerCount = 0
        self.message_id = None
        self._floodwait = False
        self.doc_message_id = None
        self.__url = _TG_API.format(token)
        _PAYLOAD.update({"chat_id": chat})
        StreamHandler.__init__(self)

    def __str__(self):
        tcount = self.triggerCount
        ecount = self.editCount
        active = self.active
        return f"Total Queued Items - {len(self.log_db)} \nActive - {active} \nTriggered - {tcount} times \nTotal edits - {ecount} times."

    def __clear(self, *args):
        __DO_NOT_ACCESS__.clear()

    def emit(self, record):
        msg = self.format(record)
        self.log_db.append("\n\n\n" + msg)
        self.triggerCount += 1
        if not (self.active or self._floodwait):
            self.active = True
            task = loop.create_task(self.runQueue())
            __DO_NOT_ACCESS__.append(task)
            task.add_done_callback(self.__clear)

    async def runQueue(self):
        await asyncio.sleep(3)
        if not self.log_db:
            self.active = False
            return
        self.active = True
        await self.handle_logs(self.log_db.copy())
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
        if lst[0] != self.current.replace("```", ""):
            await self.edit_message(lst[0], sleep=5)
        for i in lst[1:]:
            await self.send_message(i, sleep=randrange(6, 15))

    async def handle_logs(self, db):
        msgs = "".join(db)
        edit_left = _TG_MSG_LIMIT - len(self.current)
        as_file = any(len(i) > _TG_MSG_LIMIT for i in db)
        if edit_left > len(msgs):
            await self.edit_message(self.current + msgs, sleep=randrange(5, 12))
        elif as_file or len(msgs) > _MAX_LOG_LIMIT:
            await self.send_file(msgs, sleep=randrange(8, 15))
        else:
            await self.conditionX(db)
        self.log_db = self.log_db[len(db) :]

    async def send_request(self, url, payload):
        async with ClientSession() as session:
            async with session.request("POST", url, json=payload) as response:
                return await response.json()

    async def cancel_floodwait(self, sleep):
        await asyncio.sleep(sleep)
        self._floodwait = False

    async def send_message(self, message, sleep):
        payload = deepcopy(_PAYLOAD)
        if message.startswith("\n\n\n"):
            message = message[3:]
        payload["text"] = f"```{message}```"
        if ids := self.message_id or self.doc_message_id:
            payload["reply_to_message_id"] = ids
        res = await self.send_request(self.__url + "/sendMessage", payload)
        if res.get("ok"):
            self.message_id = int(res["result"]["message_id"])
            self.current = message
            self.doc_message_id = None
            await asyncio.sleep(sleep)
        else:
            await self.handle_error(res)

    async def edit_message(self, message, sleep):
        if message.startswith("\n\n\n"):
            message = message[3:]
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
            payload["reply_to_message_id"] = ids
        files = {"document": file}
        payload.pop("disable_web_page_preview", None)
        async with ClientSession() as session:
            async with session.request(
                "POST", url, params=payload, data=files
            ) as response:
                res = await response.json()
        if res.get("ok"):
            self.doc_message_id = int(res["result"]["message_id"])
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
            print(f"floodwait in tglogging of {s}")
            sleep = s + (s // 3)
            task = loop.create_task(cancel_floodwait(sleep))
            __DO_NOT_ACCESS__.append(task)
