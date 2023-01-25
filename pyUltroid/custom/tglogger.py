# Original Source : https://github.com/subinps/tglogging
# Modified to make compatible with Ultroid.
#
# first push: 24-09-2022, v0.7
# fixes: 23-01-2023, v0.8

import asyncio
from io import BytesIO
from logging import StreamHandler

from aiohttp import ClientSession

from ._loop import loop


_TG_MSG_LIMIT = 4020
_MAX_LOG_LIMIT = 12000
_TG_API = "https://api.telegram.org/bot{}"
_PAYLOAD = {"disable_web_page_preview": True, "parse_mode": "Markdown"}


class TGLogHandler(StreamHandler):
    def __init__(self, chat, token):
        self.chat = chat
        self.log_db = []
        self.current = ""
        self.active = False
        self.editCount = 0
        self.message_id = None
        self._floodwait = False
        self.async_tasks = set()
        self.doc_message_id = None
        self.__tgtoken = _TG_API.format(token)
        _PAYLOAD.update({"chat_id": chat})
        StreamHandler.__init__(self)

    def __str__(self):
        ecount = self.editCount
        active = self.active
        return f"Total Queued Items: {len(self.log_db)} \n{active = } \nEdited {ecount} times."

    def __clear(self, *args):
        self.async_tasks.clear()

    def emit(self, record):
        msg = self.format(record)
        self.log_db.append("\n\n\n" + msg)
        if not (self.active or self._floodwait):
            self.active = True
            task = loop.create_task(self.runQueue())
            self.async_tasks.add(task)
            task.add_done_callback(self.__clear)

    async def runQueue(self):
        await asyncio.sleep(3)
        if not self.log_db:
            self.active = False
            return
        self.active = True
        await self.handle_logs(self.log_db.copy())
        await asyncio.sleep(8)
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
            await self.edit_message(lst[0])
        for i in lst[1:]:
            await self.send_message(i)
            await asyncio.sleep(8)

    async def handle_logs(self, db):
        msgs = "".join(db)
        edit_left = _TG_MSG_LIMIT - len(self.current)
        as_file = any(len(i) > _TG_MSG_LIMIT for i in db)
        if edit_left > len(msgs):
            await self.edit_message(self.current + msgs)
        elif as_file or len(msgs) > _MAX_LOG_LIMIT:
            await self.send_file(msgs)
        else:
            await self.conditionX(db)
        self.log_db = self.log_db[len(db) :]

    async def send_request(self, url, payload):
        async with ClientSession() as session:
            async with session.request("POST", url, json=payload) as response:
                return await response.json()

    def handle_floodwait(self):
        self._floodwait = False

    async def send_message(self, message):
        payload = _PAYLOAD.copy()
        if message.startswith("\n\n\n"):
            message = message[3:]
        payload["text"] = f"```{message}```"
        if ids := self.message_id or self.doc_message_id:
            payload["reply_to_message_id"] = ids
        res = await self.send_request(self.__tgtoken + "/sendMessage", payload)
        if res.get("ok"):
            self.message_id = int(res["result"]["message_id"])
            self.current = message
            self.doc_message_id = None
        else:
            await self.handle_error(res)

    async def edit_message(self, message):
        if message.startswith("\n\n\n"):
            message = message[3:]
        if not self.message_id:
            await self.send_message(message)
            return
        payload = _PAYLOAD.copy()
        payload.update({"message_id": self.message_id, "text": f"```{message}```"})
        res = await self.send_request(self.__tgtoken + "/editMessageText", payload)
        if res.get("ok"):
            self.editCount += 1
            self.current = message
        else:
            await self.handle_error(res)

    async def send_file(self, logs):
        file = BytesIO(logs.encode())
        file.name = "tglogging.txt"
        url = self.__tgtoken + "/sendDocument"
        payload = _PAYLOAD.copy()
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
            self.editCount += 1
            self.doc_message_id = int(res["result"]["message_id"])
            self.current = ""
            self.message_id = None
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
            print(f"tglogger: floodwait of {s}s")
            loop.call_later(s + (s // 4), self.handle_floodwait)
