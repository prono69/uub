# written by @ah3h3!
# bash taken from Userge.

import asyncio
import os
import subprocess
import sys
import threading
import time
import traceback
from io import StringIO
from getpass import getuser
from shlex import quote as shquote, split as shsplit
from typing import Awaitable, Any, Callable, Dict, Optional, Tuple, Iterable

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified

from pyUltroid import LOGS, udB
from ..helper import _HANDLERS, _AUTH_USERS

try:
    from os import setsid, killpg, getpgid
    from signal import SIGKILL
except ImportError:
    setsid = None
    from os import kill as killpg
    from signal import CTRL_C_EVENT as SIGKILL

    def getpgid(arg):
        return arg


# ~~~~~~~~~~~~~~~~~~~~ Eval ~~~~~~~~~~~~~~~~~~~~~~~~~~


async def apexec(code, client, message):
    exec(
        f"async def __aexec(client, message): "
        + "\n  app = client"
        + "\n  chat = message.chat.id"
        + "\n  m = message"
        + "\n  p = print"
        + "\n  rm = reply = message.reply_to_message \n"
        + "".join(f"\n  {l}" for l in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)


@Client.on_message(
    filters.command("eval", prefixes=_HANDLERS) & filters.user(_AUTH_USERS)
)
@Client.on_edited_message(
    filters.command("eval", prefixes=_HANDLERS) & filters.user(_AUTH_USERS)
)
async def _eval(client, m: Message):
    try:
        cmd = m.text.split(maxsplit=1)[1]
    except IndexError:
        return await m.reply_text("Give Command as well :)", quote=True)

    status = await m.reply_text("`Processing...`", quote=True)
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    stdout, stderr, exc = None, None, None
    try:
        await apexec(cmd, client, m)
    except Exception:
        exc = traceback.format_exc()
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    evaluation = ""
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "Success"

    final_output = f"**>**  `{cmd}` \n\n**>>**  `{evaluation.strip()}`"
    if len(final_output) > 4096:
        filename = "eval_pyro.txt"
        out = str(final_output).replace("`", "").replace("*", "").replace("_", "")
        with open(filename, "w+", encoding="utf8") as out_file:
            out_file.write(out)
        await m.reply_document(
            document=filename,
            caption=f"**>>** `{cmd[:1024]}`",
            disable_notification=True,
        )
        os.remove(filename)
        await status.delete()
    else:
        await status.edit(str(final_output))


# ~~~~~~~~~~~~~~~~~~~~ Bash ~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def bash(cmd):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        executable=os.environ.get("SHELL", "/bin/bash"),
    )
    stdout, stderr = await process.communicate()
    err = stderr.decode(errors="replace").strip() or None
    out = stdout.decode(errors="replace").strip()
    return out, err


@Client.on_message(
    filters.command(["bash", "term"], prefixes=_HANDLERS) & filters.user(_AUTH_USERS)
)
@Client.on_edited_message(
    filters.command(["bash", "term"], prefixes=_HANDLERS) & filters.user(_AUTH_USERS)
)
async def terminal_(client, m):
    """run commands in bash terminal with live update"""
    try:
        parsed_cmd = m.text.split(maxsplit=1)[1]
    except IndexError:
        return await m.reply_text("Give some cmd too", quote=True)

    msg = await m.reply_text("`Processing ...`", quote=True)
    try:
        t_obj = await Term.execute(parsed_cmd)
    except Exception as t_e:
        LOGS.exception(t_e)
        return await msg.edit("**Error:** " + str(t_e))

    output = f"**{getuser()}:~#** ```{parsed_cmd}``` \n"
    await t_obj.init()
    while not t_obj.finished:
        try:
            await msg.edit(f"{output}```{t_obj.line}```")
            await t_obj.wait(5)
        except MessageNotModified:
            pass
        except BaseException:
            t_obj.cancel()
            return LOGS.exception(BaseException)

    if t_obj.cancelled:
        return await msg.edit("__Terminal process Cancelled!__")

    out_data = f"{output}```{t_obj.output}```"
    if len(out_data) > 4096:
        fn = "terminal_.txt"
        with open(fn, "w+") as f:
            f.write(out_data)
        await msg.reply_document(fn, caption=f"`{parsed_cmd[:1024]}`")
        os.remove(fn)
    else:
        await msg.edit(out_data)


class Term:
    """live update term class"""

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        self._process = process
        self._line = b""
        self._output = b""
        self._init = asyncio.Event()
        self._is_init = False
        self._cancelled = False
        self._finished = False
        self._loop = asyncio.get_running_loop()
        self._listener = self._loop.create_future()

    @property
    def line(self) -> str:
        return self._by_to_str(self._line)

    @property
    def output(self) -> str:
        return self._by_to_str(self._output)

    @staticmethod
    def _by_to_str(data: bytes) -> str:
        return data.decode("utf-8", "replace").strip()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def finished(self) -> bool:
        return self._finished

    async def init(self) -> None:
        await self._init.wait()

    async def wait(self, timeout: int) -> None:
        self._check_listener()
        try:
            await asyncio.wait_for(self._listener, timeout)
        except asyncio.TimeoutError:
            pass

    def _check_listener(self) -> None:
        if self._listener.done():
            self._listener = self._loop.create_future()

    def cancel(self) -> None:
        if self._cancelled or self._finished:
            return
        killpg(getpgid(self._process.pid), SIGKILL)
        self._cancelled = True

    @classmethod
    async def execute(cls, cmd: str) -> "Term":
        kwargs = dict(
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable=os.environ.get("SHELL", "/bin/bash"),
        )
        if setsid:
            kwargs["preexec_fn"] = setsid
        process = await asyncio.create_subprocess_shell(cmd, **kwargs)
        t_obj = cls(process)
        t_obj._start()
        return t_obj

    def _start(self) -> None:
        self._loop.create_task(self._worker())

    async def _worker(self) -> None:
        if self._cancelled or self._finished:
            return
        await asyncio.wait([self._read_stdout(), self._read_stderr()])
        await self._process.wait()
        self._finish()

    async def _read_stdout(self) -> None:
        await self._read(self._process.stdout)

    async def _read_stderr(self) -> None:
        await self._read(self._process.stderr)

    async def _read(self, reader: asyncio.StreamReader) -> None:
        while True:
            line = await reader.readline()
            if not line:
                break
            self._append(line)

    def _append(self, line: bytes) -> None:
        self._line = line
        self._output += line
        self._check_init()

    def _check_init(self) -> None:
        if self._is_init:
            return
        self._loop.call_later(1, self._init.set)
        self._is_init = True

    def _finish(self) -> None:
        if self._finished:
            return
        self._init.set()
        self._finished = True
        if not self._listener.done():
            self._listener.set_result(None)
