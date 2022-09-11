# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("help_devtools")

import inspect
import sys
import traceback
from io import BytesIO, StringIO
from os import remove
from pprint import pprint
from random import choice

from telethon.utils import get_display_name

from pyUltroid import _ignore_eval
from pyUltroid.fns.multi_db import *
from pyUltroid.fns._transfer import pyroUL, pyroDL

from . import *

# Used for Formatting Eval Code, if installed
try:
    import black
except ImportError:
    black = None

try:
    from yaml import safe_load
except ImportError:
    from pyUltroid.fns.tools import safe_load

try:
    from telegraph import upload_file as uf
except ImportError:
    uf = None

from telethon.tl import functions

fn = functions


@ultroid_cmd(
    pattern="(sysinfo|neofetch)$",
)
async def _(e):
    xx = await e.eor(get_string("com_1"))
    x, y = await bash("neofetch|sed 's/\x1B\\[[0-9;\\?]*[a-zA-Z]//g' >> neo.txt")
    if y and y.endswith("NOT_FOUND"):
        return await xx.edit(f"Error: `{y}`")
    np = await asyncread("neo.txt")
    all_col = (await asyncread("resources/colorlist.txt")).splitlines()
    p = np.replace("\n\n", "")
    haa = await Carbon(code=p, file_name="neofetch", backgroundColor=choice(all_col))
    await e.reply(file=haa)
    await xx.delete()
    remove("neo.txt")


@ultroid_cmd(pattern="bash", fullsudo=True, only_devs=True)
async def _(event):
    carb, yamlf = None, False
    try:
        cmd = event.text.split(" ", maxsplit=1)[1]
        if cmd.split()[0] in ["-c", "--carbon"]:
            cmd = cmd.split(maxsplit=1)[1]
            carb = True
    except IndexError:
        return await event.eor(get_string("devs_1"), time=10)
    xx = await event.eor(get_string("com_1"))
    LOGS.debug(cmd)
    reply_to_id = event.reply_to_msg_id or event.id
    stdout, stderr = await bash(cmd, run_code=1)
    OUT = f"**☞ BASH\n\n• COMMAND:**\n`{cmd}` \n\n"
    err, out = "", ""
    if stderr:
        err = f"**• ERROR:** \n`{stderr}`\n\n"
    if stdout:
        if carb or udB.get_key("CARBON_ON_BASH"):
            colors = (await asyncread("resources/colorlist.txt")).splitlines()
            li = await Carbon(
                code=stdout,
                file_name="_bash",
                download=True,
                backgroundColor=choice(colors),
            )
            url = await get_imgbb_link(
                "_bash.jpg",
                hq=True,
                expire=7200,
                delete=True,
                preview=True,
            )
            # url = f"https://graph.org{uf(li)[-1]}"
            OUT = f"[\xad]({url}){OUT}"
            out = "**• OUTPUT:**"
        else:
            if "pip" in cmd and all(":" in line for line in stdout.split("\n")):
                try:
                    load = safe_load(stdout)
                    stdout = ""
                    for data in list(load.keys()):
                        res = load[data] or ""
                        if res and "http" not in str(res):
                            res = f"`{res}`"
                        stdout += f"**{data}**  :  {res}\n"
                    yamlf = True
                except Exception as er:
                    stdout = f"`{stdout}`"
                    LOGS.exception(er)
            else:
                stdout = f"`{stdout}`"
            out = f"**• OUTPUT:**\n{stdout}"
    if not stderr and not stdout:
        out = "**• OUTPUT:**\n`Success`"
    OUT += err + out
    if len(OUT) > 4096:
        ultd = err + out
        with BytesIO(str.encode(ultd)) as out_file:
            out_file.name = "bash.txt"
            await event.client.send_file(
                event.chat_id,
                out_file,
                force_document=True,
                thumb=ULTConfig.thumb,
                allow_cache=False,
                caption=f"```{cmd[:1000]}```",
                reply_to=reply_to_id,
            )

            await xx.delete()
    else:
        await xx.edit(OUT, link_preview=not yamlf)
    asst.loop.create_task(evalogger(cmd, event))


pp = pprint  # ignore: pylint
bot = ultroid = ultroid_bot


class u:
    ...


def _parse_eval(value=None):
    if not value:
        return value
    if hasattr(value, "stringify"):
        try:
            return value.stringify()
        except TypeError:
            pass
    elif isinstance(value, dict):
        try:
            return json_parser(value, indent=1)
        except BaseException:
            pass
    return str(value)


@ultroid_cmd(pattern="eval", fullsudo=True, only_devs=True)
async def _(event):
    try:
        cmd = event.text.split(maxsplit=1)[1]
    except IndexError:
        return await event.eor(get_string("devs_2"), time=5)
    silent, gsource, xx, carb = False, False, None, False
    spli = cmd.split()

    async def get_():
        try:
            cm = cmd.split(maxsplit=1)[1]
        except IndexError:
            await event.eor("->> Wrong Format <<-")
            cm = None
        return cm

    if spli[0] in ["-s", "--silent"]:
        await event.delete()
        silent = True
        cmd = await get_()
    elif spli[0] in ["-c", "--carbon"]:
        carb = True
        cmd = await get_()
    elif spli[0] in ["-n", "-noedit"]:
        cmd = await get_()
        xx = await event.reply(get_string("com_1"))
    elif spli[0] in ["-gs", "--source"]:
        gsource = True
        cmd = await get_()

    if not cmd:
        return

    if not silent and not xx:
        xx = await event.eor(get_string("com_1"))
    if event.chat_id != -1001774703582:
        LOGS.debug(cmd)
    if black:
        try:
            cmd = black.format_str(cmd, mode=black.Mode())
        except BaseException:
            # Consider it as Code Error, and move on to be shown ahead.
            pass

    reply_to_id = event.reply_to_msg_id or event
    if any(item in cmd for item in KEEP_SAFE().All) and (
        not (event.out or event.sender_id == ultroid_bot.uid)
    ):
        warning = await event.forward_to(udB.get_key("LOG_CHANNEL"))
        await warning.reply(
            f"Malicious Activities suspected by {inline_mention(await event.get_sender())}"
        )
        if not udB.get_key("_SKIP_WARNINGS"):
            _ignore_eval.append(event.sender_id)
            return await xx.edit(
                "`Malicious Activities suspected⚠️!\nReported to owner. Aborted this request!`"
            )
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    stdout, stderr, exc, timeg = None, None, None, None
    tima = time.time()
    try:
        value = await aexec(cmd, event)
    except Exception:
        value = None
        exc = traceback.format_exc()
    tima = time.time() - tima
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    if value and gsource:
        try:
            exc = inspect.getsource(value)
        except Exception:
            exc = traceback.format_exc()
    evaluation = exc or stderr or stdout or _parse_eval(value) or get_string("instu_4")
    if silent:
        if exc:
            msg = f"• <b>EVAL ERROR\n\n• CHAT:</b> <code>{get_display_name(event.chat)}</code> [<code>{event.chat_id}</code>]"
            msg += f"\n\n∆ <b>CODE:</b>\n<code>{cmd}</code>\n\n∆ <b>ERROR:</b>\n<code>{exc}</code>"
            log_chat = udB.get_key("LOG_CHANNEL")
            if len(msg) > 4000:
                with BytesIO(msg.encode()) as out_file:
                    out_file.name = "Eval-Error.txt"
                return await event.client.send_message(
                    log_chat, f"`{cmd}`", file=out_file
                )
            await event.client.send_message(log_chat, msg, parse_mode="html")
        return
    tmt = tima * 1000
    timef = time_formatter(tmt)
    timeform = timef if not timef == "0s" else f"{tmt:.3f}ms"
    if carb:
        colors = (await asyncread("resources/colorlist.txt")).splitlines()
        lin = await Carbon(
            code=evaluation,
            file_name="_eval",
            download=True,
            backgroundColor=choice(colors),
        )
        url = await get_imgbb_link(
            "_eval.jpg",
            hq=True,
            expire=7200,
            delete=True,
            preview=True,
        )
        final_output = f"__►__ **EVAL** (__{timeform}__)\n```{cmd}``` \n\n __►__ **OUTPUT**: [⁮⁮⁮\xad]({url})"
    else:
        final_output = "__►__ **EVAL** (__{}__)\n```{}``` \n\n __►__ **OUTPUT**: \n```{}``` \n".format(
            timeform,
            cmd,
            evaluation,
        )
    if len(final_output) > 4096:
        final_output = evaluation
        with BytesIO(str.encode(final_output)) as out_file:
            out_file.name = "eval.txt"
            await event.client.send_file(
                event.chat_id,
                out_file,
                force_document=True,
                thumb=ULTConfig.thumb,
                allow_cache=False,
                caption=f"```{cmd[:1000]}```",
                reply_to=reply_to_id,
            )
        return await xx.delete()
    await xx.edit(final_output, link_preview=carb)
    asst.loop.create_task(evalogger(cmd, event))


def _stringify(text=None, *args, **kwargs):
    if text:
        u._ = text
        text = _parse_eval(text)
    return print(text, *args, **kwargs)


async def evalogger(cmd, e):
    await asyncio.sleep(1)
    msg = "<b>CMD Executed!</b> \n\n<code>{0}</code> \n\n–  {1}:  {2} \n–  <a href='{3}'>{4}</a>"
    sndr = e.sender or await e.get_sender()
    try:
        _msg = msg.format(
            cmd,
            get_display_name(sndr),
            inline_mention(sndr, custom=sndr.id, html=True),
            await msg_link(e),
            get_display_name(e.chat or await e.get_chat()),
        )
        await asst.send_message(TAG_LOG, _msg, link_preview=False, parse_mode="html")
    except BaseException:
        return LOGS.exception("EVAL Logger error")


async def aexec(code, event):
    exec(
        (
            "async def __aexec(e, client): "
            + "\n print = p = _stringify"
            + "\n message = event = e"
            + "\n u.r = reply = rm = await event.get_reply_message()"
            + "\n chat = event.chat_id"
            + "\n u.lr = locals()"
        )
        + "".join(f"\n {l}" for l in code.split("\n"))
    )

    return await locals()["__aexec"](event, event.client)


DUMMY_CPP = """#include <iostream>
using namespace std;

int main(){
!code
}
"""


@ultroid_cmd(pattern="cpp", only_devs=True)
async def doie(e):
    match = e.text.split(" ", maxsplit=1)
    try:
        match = match[1]
    except IndexError:
        return await e.eor(get_string("devs_3"))
    msg = await e.eor(get_string("com_1"))
    if "main(" not in match:
        new_m = "".join(" " * 4 + i + "\n" for i in match.split("\n"))
        match = DUMMY_CPP.replace("!code", new_m)
    open("cpp-ultroid.cpp", "w").write(match)
    m = await bash("g++ -o CppUltroid cpp-ultroid.cpp")
    o_cpp = f"• **Eval-Cpp**\n`{match}`"
    if m[1]:
        o_cpp += f"\n\n**• Error :**\n`{m[1]}`"
        if len(o_cpp) > 3000:
            os.remove("cpp-ultroid.cpp")
            if os.path.exists("CppUltroid"):
                os.remove("CppUltroid")
            with BytesIO(str.encode(o_cpp)) as out_file:
                out_file.name = "error.txt"
                return await msg.reply(f"`{match}`", file=out_file)
        return await eor(msg, o_cpp)
    m = await bash("./CppUltroid")
    if m[0] != "":
        o_cpp += f"\n\n**• Output :**\n`{m[0]}`"
    if m[1]:
        o_cpp += f"\n\n**• Error :**\n`{m[1]}`"
    if len(o_cpp) > 3000:
        with BytesIO(str.encode(o_cpp)) as out_file:
            out_file.name = "eval.txt"
            await msg.reply(f"`{match}`", file=out_file)
    else:
        await eor(msg, o_cpp)
    os.remove("CppUltroid")
    os.remove("cpp-ultroid.cpp")
