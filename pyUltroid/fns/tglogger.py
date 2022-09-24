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
        self.count = 0
        self.chat = chat
        self.log_db = []
        self.current = ""
        self.active = False
        self.message_id = None
        self._floodwait = False
        self.__url = _TG_API.format(token)
        _PAYLOAD.update({"chat_id": chat})
        StreamHandler.__init__(self)

    def __str__(self):
        count = self.count
        active = self.active
        return f"Total Queued Items - {len(self.log_db)} | Active - {active} | Count - {count}"

    def emit(self, record):
        self.count += 1
        msg = self.format(record)
        self.log_db.append(msg)
        if not (self.active or self._floodwait):
            self.active = True
            loop.create_task(self.runQueue())

    async def runQueue(self):
        if not (db := self.log_db):
            self.active = False
            return
        self.active = True
        await self.handle_logs(db)
        await self.runQueue()

    def splitter(self, logs):
        _log = []
        current = self.current
        for l in logs:
            edit_left = _TG_MSG_LIMIT - len(current)
            if edit_left > len(l):
                current += "\n\n\n" + l
            else:
                # x, y = l[:edit_left], l[edit_left:]
                _log.append(current)
                current = l
        _log.append(current)
        return _log

    async def conditionX(self, log_msg):
        lst = self.splitter(log_msg)
        if lst[0] != self.current:
            await self.edit_message(lst[0], sleep=5)
        for i in lst[1:]:
            await self.send_message(i, sleep=randrange(8, 15))

    async def handle_logs(self, db):
        pre_len = len(db)
        temp_logs = deepcopy(db)  # db[:pre_len]
        _len = len(" ".join(temp_logs))
        edit_left = _TG_MSG_LIMIT - len(self.current)
        as_file = any(len(i) > _TG_MSG_LIMIT for i in temp_logs)

        if edit_left > _len:
            msg = self.current + "\n\n\n".join(temp_logs)
            await self.edit_message(msg, sleep=randrange(6, 13))
        elif as_file or _len > _MAX_LOG_LIMIT:
            await self.send_file("\n\n\n".join(temp_logs), sleep=randrange(10, 20))
        else:
            await self.conditionX(temp_logs)
        self.log_db = self.log_db[pre_len:]

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
        res = await self.send_request(self.__url + "/sendMessage", payload)
        if res.get("ok"):
            self.message_id = int(res["result"]["message_id"])
            self.current = message
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
            self.current += "\n\n\n" + message
            await asyncio.sleep(sleep)
        else:
            await self.handle_error(res)

    async def send_file(self, logs, sleep):
        file = BytesIO(logs.encode())
        file.name = "tglogging.txt"
        url = self.__url + "/sendDocument"
        payload = deepcopy(_PAYLOAD)
        payload["caption"] = "Too much logs to send, hence sending as file."
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
