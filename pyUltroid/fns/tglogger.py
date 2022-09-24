# Original Source : https://github.com/subinps/tglogging
# Modified to make compatible with Ultroid.
# first push : 24-09-2022, v0.7

import asyncio
from io import BytesIO
from copy import deepcopy
from random import randrange
from logging import StreamHandler
from aiohttp import ClientSession


# ----------------------------------------------------------------------------

loop = asyncio.get_event_loop()

_TG_API = "https://api.telegram.org/bot{}"
_TG_MSG_LIMIT = 4040
_PAYLOAD = {"disable_web_page_preview": True, "parse_mode": "Markdown"}
_MAX_LOG_LIMIT = 8192

# ----------------------------------------------------------------------------


class TGLogHandler(StreamHandler):
    def __init__(self, chat, token):
        self.count = 0
        self.chat = chat
        self.log_db = []
        self.current = []
        self.active = False
        self.message_id = None
        self._floodwait = False
        self.__url = _TG_API.format(token)
        self.__payload = deepcopy(_PAYLOAD)
        self.__payload.update({"chat_id": chat})
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

    async def _edit_or_send(self, log, slp):
        if not self.message_id:
            await self.send_message(f"```{log}```")
            self.current = [log]
        else:
            current = "".join([f"```{i}```\n" for i in self.current])
            await self.edit_message(current + f"```{log}```")
            self.current.append(log)
        await asyncio.sleep(slp)

    async def _send_doc(self, data):
        await self.send_as_document(data)
        self.current.clear()
        self.message_id = None
        await asyncio.sleep(randrange(8, 17))

    async def handle_edit_or_send(self, edit_left, log_msg):
        if edit_left > len(log_msg):
            await self._edit_or_send(log_msg, slp=randrange(6, 13))
            return
        to_edit_list = [log_msg[:edit_left]]
        log_msg = log_msg[edit_left:]
        temp_list = [
            log_msg[i : i + _TG_MSG_LIMIT]
            for i in range(0, len(log_msg), _TG_MSG_LIMIT)
        ]
        to_edit_list.extend([temp_list])
        del temp_list, log_msg
        for log in lst:
            await self._edit_or_send(log, slp=randrange(8, 17))

    async def handle_logs(self, db):
        pre_len = len(db)
        temp_logs = deepcopy(db)  # db[:pre_len]
        # if sum of all logs > 8192
        if sum(map(lambda i: len(i), temp_logs)) > _TG_MSG_LIMIT:
            await self._send_doc(temp_logs)
            self.log_db = self.log_db[pre_len:]
            return
        for log in temp_logs:
            edit_left = _TG_MSG_LIMIT - len("".join(self.current))
            await self.handle_edit_or_send(edit_left, log)
        self.log_db = self.log_db[pre_len:]

    async def send_request(self, url, payload):
        async with ClientSession() as session:
            async with session.request("POST", url, json=payload) as response:
                return await response.json()

    async def cancel_floodwait(self, sleep):
        await asyncio.sleep(sleep)
        self._floodwait = False

    async def send_message(self, message):
        payload = deepcopy(self.__payload)
        payload["text"] = message
        res = await self.send_request(self.__url + "/sendMessage", payload)
        if res.get("ok"):
            self.message_id = res["result"]["message_id"]
        else:
            await self.handle_error(res)

    async def edit_message(self, message):
        payload = deepcopy(PAYLOAD)
        payload.update({"message_id": self.message_id, "text": message})
        res = await self.send_request(self.__url + "/editMessageText", payload)
        if not res.get("ok"):
            await self.handle_error(res)

    async def send_as_document(self, logs):
        file = BytesIO(logs.encode())
        file.name = "tglogging.txt"
        url = self.__url + "/sendDocument"
        payload = deepcopy(PAYLOAD)
        payload["caption"] = "Too much logs to send, hence sending as file."
        files = {"document": file}
        payload.pop("disable_web_page_preview", None)
        async with ClientSession() as session:
            async with session.request(
                "POST", url, params=payload, data=files
            ) as response:
                res = await response.json()
        if not res.get("ok"):
            await self.handle_error(res)
        # print("Logs send as a file since there were too much lines to print.")

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


# ----------------------------------------------------------------------------
