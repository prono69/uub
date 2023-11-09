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
from pathlib import Path
from pprint import pprint
from random import choice

from telethon.utils import get_display_name

from pyUltroid import _ignore_eval
from pyUltroid.custom.multi_db import *
from pyUltroid.custom._transfer import pyroUL, pyroDL

from . import *
from plugins import _get_colors

try:
    from yaml import safe_load
except ImportError:
    from pyUltroid.fns.tools import safe_load

try:
    from telegraph import upload_file as uf
except ImportError:
    uf = None

try:
    from rich.pretty import Pretty
except ImportError:
    Pretty = None
else:
    from rich.console import Console

from telethon.tl import functions

fn = functions


@ultroid_cmd(
    pattern="(sysinfo|neofetch)$",
)
async def neo_fetch(e):
    xx = await e.eor(get_string("com_1"))
    x, y = await bash("neofetch|sed 's/\x1B\\[[0-9;\\?]*[a-zA-Z]//g' >> neo.txt")
    if y and y.endswith("NOT_FOUND"):
        return await xx.edit(f"Error: `{y}`")
    np = await asyncread("neo.txt")
    color = await _get_colors(pick=True)
    p = np.replace("\n\n", "")
    haa = await Carbon(code=p, file_name="neofetch", backgroundColor=color)
    if isinstance(haa, dict):
        return await xx.edit(f"`{haa}`")
    await e.reply(file=haa)
    osremove("neo.txt")
    await xx.delete()


class u:
    _ = ""

    @staticmethod
    def _html(text, language):
        try:
            text = text.replace("<", "&lt;").replace(">", "&gt;")
        except Exception:
            pass
        return f"""<pre><code class="language-{language}">{text}</code></pre>"""

    @staticmethod
    async def _evalogger(cmd, e, format_lang):
        await asyncio.sleep(2)
        msg = "<b><blockquote>CMD Executed!</blockquote></b> \n\n{0}\n\n–  {1}:  {2} \n–  <a href='{3}'>{4}</a>"
        sndr = e.sender or await e.get_sender()
        try:
            _msg = msg.format(
                u._html(cmd, format_lang),
                get_display_name(sndr),
                inline_mention(sndr, custom=sndr.id, html=True),
                e.message_link,
                get_display_name(e.chat or await e.get_chat()),
            )
            await asst.send_message(
                TAG_LOG,
                _msg,
                link_preview=False,
                parse_mode="html",
            )
        except Exception:
            return LOGS.exception("EVAL Logger error")


@ultroid_cmd(
    pattern=r"bash( ([\s\S]*))",
    fullsudo=True,
    only_devs=True,
)
async def run_bash(event):
    cmd = event.pattern_match.group(2)
    if not cmd:
        return await event.eor(get_string("devs_1"), time=5)

    carb, rayso, nolog, _url = False, False, False, None
    try:
        _spl = cmd.split(maxsplit=1)
        if _spl[0] == "-c":  # carbon
            cmd = _spl[1]
            carb = True
        elif _spl[0] == "-r":  # rayso
            cmd = _spl[1]
            rayso = True
        elif _spl[0] == "-nl":  # nolog
            cmd = _spl[1]
            nolog = True
    except IndexError:
        return await event.eor(get_string("devs_1"), time=10)

    if not nolog:
        LOGS.debug(cmd)
    xx = await event.eor(get_string("com_1"))

    stdout, stderr = await bash(cmd, run_code=1)
    if stdout and (carb or rayso):
        color = await _get_colors(pick=True)
        li = await Carbon(
            code=stdout,
            file_name="_bash",
            download=True,
            backgroundColor=color,
            rayso=rayso,
        )
        if not isinstance(li, dict):
            _url = await get_imgbb_link(
                "_bash.jpg",
                hq=True,
                expire=7200,
                delete=True,
                preview=True,
            )
            await asyncio.sleep(2)

    if not (carb or rayso) and len(cmd + str(stderr) + str(stdout)) > 4000:
        OUT = f"☞ BASH\n\n\n• COMMAND:\n{cmd} \n\n\n"
        if not (stderr and stdout):
            OUT += f"• OUTPUT:\nSuccess"
        else:
            if stderr:
                OUT += f"• ERROR:\n{stderr} \n\n\n"
            OUT += f"• OUTPUT:\n{stdout}"

        with BytesIO(OUT.encode()) as out_file:
            out_file.name = "bash.txt"
            caption = "<b>• BASH:</b>\n" + u._html(
                cmd if len(cmd) < 610 else cmd[:600] + " ...", "bash"
            )
            await event.client.send_file(
                event.chat_id,
                out_file,
                force_document=True,
                thumb=ULTConfig.thumb,
                allow_cache=False,
                caption=caption,
                parse_mode="html",
                reply_to=event.reply_to_msg_id,
            )
        await xx.delete()
        return

    _cmd = u._html(cmd, "bash")
    OUT = f"""<b>☞ BASH\n\n• COMMAND:</b>\n{_cmd}\n\n"""
    if stderr:
        OUT += f"<b>• ERROR:</b>\n"
        OUT += u._html(stderr, "") + "\n\n"
    if not (stderr or stdout):
        OUT += f"<b>• OUTPUT:</b>\n"
        OUT += u._html("Success", "")
    if stdout or _url:
        OUT += "<b>• OUTPUT:</b>\n"
        OUT += f"<a href='{_url}'>\xad</a>" if _url else u._html(stdout, "")
    await xx.edit(OUT, parse_mode="html", link_preview=bool(_url))
    if not nolog:
        await u._evalogger(cmd, event, "bash")


pp = pprint  # ignore: pylint
bot = ultroid = ultroid_bot


def _parse_eval(value=None):
    if not value:
        return value

    if hasattr(value, "stringify"):
        try:
            return value.stringify()
        except TypeError:
            return value

    if Pretty:
        pretty_obj = Pretty(
            value,
            indent_guides=False,
            expand_all=True,
            indent_size=4,
            overflow="ignore",
        )
        tmp_file = StringIO()
        rich_console = Console(file=tmp_file)
        rich_console.print(pretty_obj, crop=False)
        return tmp_file.getvalue()

    if isinstance(value, dict):
        try:
            return json_parser(value, indent=4)
        except Exception:
            return value
    elif isinstance(value, (list, tuple, set)):
        _dict = {list: ("[", "]"), tuple: ("(", ")"), set: ("{", "}")}
        st_symbol, end_symbol = _dict[type(value)]
        for child in value:
            if type(child) == str:
                st_symbol += f'\n  "{child}",'
            elif type(child) == int:
                st_symbol += f"\n  {child},"
            else:
                st_symbol += f"\n  {_parse_eval(child)},"
            # if index < len(value) - 1:
            # st_symbol += ","
        st_symbol += "\n" + end_symbol
        return st_symbol
    return value


@ultroid_cmd(
    pattern=r"eval( ([\s\S]*))",
    fullsudo=True,
    only_devs=True,
)
async def run_eval(event):
    cmd = event.pattern_match.group(2)
    if not cmd:
        return await event.eor(get_string("devs_2"), time=5)

    xx, mode = None, ""
    spli = cmd.split(maxsplit=1)

    async def get_():
        try:
            cm = cmd.split(maxsplit=1)[1]
        except IndexError:
            await event.eor("->> Wrong Format <<-")
            cm = None
        return cm

    if spli[0] == "-s":  # --silent
        if event.out:
            await event.delete()
        mode = "silent"
    elif spli[0] == "-n":  # --noedit
        mode = "no-edit"
        xx = await event.reply(get_string("com_1"))
    elif spli[0] == "-c":  # --carbon
        mode = "carb"
    elif spli[0] == "-r":  # --rayso
        mode = "rayso"
    elif spli[0] == "-nl":
        mode = "nolog"
    elif spli[0] == "-b":  # --black
        mode = "black"
    elif spli[0] == "-gs":  # --gsource
        mode = "gsource"
    elif spli[0] == "-ga":  # --gargs
        mode = "gargs"
    if mode:
        cmd = await get_()

    if not cmd:
        return

    if mode != "silent" and not xx:
        xx = await event.eor(get_string("com_1"))
    if mode != "nolog":
        LOGS.debug(cmd)
    if mode == "black":
        try:
            import black

            cmd = black.format_str(cmd, mode=black.Mode())
        except (ImportError, Exception):
            pass

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
    stdout, stderr, exc, timeg = None, None, None, None
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    try:
        tima = time.perf_counter()
        value = await aexec(cmd, event)
    except Exception:
        value = None
        exc = traceback.format_exc()
    finally:
        tima = time.perf_counter() - tima
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    if value:
        try:
            if mode == "gsource":
                exc = inspect.getsource(value)
            elif mode == "gargs":
                args = inspect.signature(value).parameters.values()
                name = ""
                if hasattr(value, "__name__"):
                    name = value.__name__
                exc = f"<b>{name}</b>\n\n" + "\n ".join([str(arg) for arg in args])
        except Exception:
            exc = traceback.format_exc()

    evaluation = exc or stderr or stdout or _parse_eval(value) or get_string("instu_4")
    if mode == "silent":
        if exc:
            log_chat = udB.get_key("LOG_CHANNEL")
            if len(exc + cmd) < 4000:
                _cmd = u._html(cmd, "python")
                msg = f"• <b>EVAL ERROR\n\n• CHAT:</b> <code>{get_display_name(event.chat)}</code> [<code>{event.chat_id}</code>] \n\n"
                msg += (
                    f"""∆ <b>CODE:</b>\n{_cmd}\n\n∆ <b>ERROR:</b>\n{u._html(exc, '')}"""
                )
                await event.client.send_message(log_chat, msg, parse_mode="html")
            else:
                msg = f"• EVAL ERROR\n\n• CHAT: {get_display_name(event.chat)} [{event.chat_id}]\n\n∆ CODE:\n{cmd}\n\n∆ ERROR:\n{exc}"
                with BytesIO(msg.encode()) as out_file:
                    out_file.name = "Eval-Error.txt"
                    caption = "<b>• EVAL:</b>\n" + u._html(
                        cmd if len(cmd) < 610 else cmd[:600] + " ...", "python"
                    )
                    await event.client.send_file(
                        log_chat,
                        out_file,
                        caption=caption,
                        parse_mode="html",
                        allow_cache=False,
                        force_document=True,
                        thumb=ULTConfig.thumb,
                    )
        return

    _url, tmt = None, tima * 1000
    timef = time_formatter(tmt)
    timeform = timef if not timef == "0s" else f"{tmt:.3f}ms"
    if mode in {"carb", "rayso"}:
        color = await _get_colors(pick=True)
        lin = await Carbon(
            code=evaluation,
            file_name="_eval",
            download=True,
            rayso=mode == "rayso",
            backgroundColor=color,
        )
        if not isinstance(lin, dict):
            _url = await get_imgbb_link(
                "_eval.jpg",
                hq=True,
                expire=7200,
                delete=True,
                preview=True,
            )
            await asyncio.sleep(2)

    if mode not in {"carb", "rayso"} and len(cmd + str(evaluation)) > 4000:
        final_output = f"► EVAL  ({timeform})\n{cmd} \n\n\n ► OUTPUT: \n{evaluation}"
        with BytesIO(final_output.encode()) as out_file:
            out_file.name = "eval.txt"
            caption = "<b>• EVAL:</b>\n" + u._html(
                cmd if len(cmd) < 610 else cmd[:600] + " ...", "python"
            )
            await event.client.send_file(
                event.chat_id,
                out_file,
                force_document=True,
                thumb=ULTConfig.thumb,
                allow_cache=False,
                caption=caption,
                parse_mode="html",
                reply_to=event.reply_to_msg_id,
            )
        await xx.delete()
        return

    _cmd = u._html(cmd, "python")
    final_output = f"""<i>►</i> <b>EVAL</b> (<i>{timeform}</i>)\n{_cmd}\n\n<i>►</i> <b>OUTPUT:</b>\n"""
    final_output += (
        f"<a href='{_url}'>⁮⁮⁮\xad</a>" if _url else u._html(evaluation, "python")
    )
    await xx.edit(final_output, parse_mode="html", link_preview=bool(_url))
    if mode != "nolog":
        await u._evalogger(cmd, event, "python")


def _stringify(text=None, *args, **kwargs):
    if text:
        # u._ = text
        text = _parse_eval(text)
    return print(text, *args, **kwargs)


async def aexec(code, event):
    exec(
        (
            "async def __aexec(e, client): "
            + "\n from builtins import print as ppp"
            + "\n\n print = p = _stringify"
            + "\n message = event = e"
            + "\n reply = rm = await event.get_reply_message()"
            + "\n chat = event.chat_id"
            # + "\n u.lr = locals()"
        )
        + "".join(f"\n {l}" for l in code.split("\n"))
    )

    return await locals()["__aexec"](event, event.client)


DUMMY_CPP = """#include <iostream>
using namespace std;

int main(){
!code
}"""


@ultroid_cmd(
    pattern=r"cpp( ([\s\S]*)|$)",
    only_devs=True,
    fullsudo=True,
)
async def cpp_compiler(e):
    match = e.pattern_match.group(2)
    if not match:
        return await e.eor(get_string("devs_3"))

    msg = await e.eor(get_string("com_1"))
    if "main(" not in match:
        new_m = "".join(" " * 4 + i + "\n" for i in match.split("\n"))
        match = DUMMY_CPP.replace("!code", new_m)

    await asyncwrite("cpp-ultroid.cpp", match, mode="w+")
    osremove("CppUltroid")
    m = await bash("g++ -o CppUltroid cpp-ultroid.cpp")
    if m[1]:
        if len(match + m[1]) < 3000:
            _match = u._html(match, "cpp")
            o_cpp = f"""• <b>Eval-Cpp</b>\n{_match}\n\n• <b>ERROR:</b>\n"""
            o_cpp += u._html(m[1], "")
            await msg.edit(o_cpp, parse_mode="html")
        else:
            o_cpp = f"• Eval-Cpp:\n{match} \n\n\n• ERROR:\n{m[1]}"
            with BytesIO(o_cpp.encode()) as out_file:
                out_file.name = "compile-error-cpp.txt"
                caption = "<b>• Eval-Cpp:</b>\n" + u._html(
                    match if len(match) < 610 else match[:600] + " ...", "cpp"
                )
                await e.client.send_file(
                    e.chat_id,
                    out_file,
                    force_document=True,
                    thumb=ULTConfig.thumb,
                    allow_cache=False,
                    caption=caption,
                    parse_mode="html",
                    reply_to=e.reply_to_msg_id,
                )
            await msg.delete()
        return osremove("cpp-ultroid.cpp", "CppUltroid")

    time_t = time.perf_counter()
    out, err = await bash("./CppUltroid")
    _time = (time.perf_counter() - time_t) * 1000
    _tfime = time_formatter(_time)
    time_t = _tfime if not _tfime == "0s" else f"{_time:.3f}ms"

    if len(match + str(out) + str(err)) > 3000:
        o_cpp = f"• Eval-Cpp: ({time_t})\n{match} \n\n\n"
        if out != "":
            o_cpp += f"• OUTPUT:\n{out}\n\n\n"
        if err:
            o_cpp += f"• ERROR:\n{err}"
        with BytesIO(o_cpp.encode()) as out_file:
            out_file.name = "cpp_output.txt"
            caption = "<b>• Eval-Cpp:</b>\n" + u._html(
                match if len(match) < 610 else match[:600] + " ...", "cpp"
            )
            await e.client.send_file(
                e.chat_id,
                out_file,
                force_document=True,
                thumb=ULTConfig.thumb,
                allow_cache=False,
                caption=caption,
                parse_mode="html",
                reply_to=e.reply_to_msg_id,
            )
        await msg.delete()
    else:
        _match = u._html(match, "cpp")
        o_cpp = f"""• <b>Eval-Cpp</b> (<i>{time_t}</i>)\n{_match}\n\n"""
        if out != "":
            o_cpp += f"• <b>OUTPUT:</b>\n"
            o_cpp += u._html(out, "") + "\n\n"
        if err:
            o_cpp += f"• <b>ERROR:</b>\n"
            o_cpp += u._html(err, "")
        await msg.edit(o_cpp, parse_mode="html")
    osremove("CppUltroid", "cpp-ultroid.cpp")
    await u._evalogger(match, e, "cpp")


# for running C code with gcc (w/o dummy cpp)
@ultroid_cmd(
    pattern=r"gcc( ([\s\S]*)|$)",
    only_devs=True,
    fullsudo=True,
)
async def _gcc_compiler(e):
    match = e.pattern_match.group(2)
    if not match:
        return await e.eor(get_string("devs_3"))

    msg = await e.eor(get_string("com_1"))
    await asyncwrite("ultroid.c", match, mode="w+")
    osremove("ultroid.out")
    m = await bash("gcc ultroid.c -o ultroid.out")

    if m[1]:
        if len(match + m[1]) < 3000:
            _match = u._html(match, "c")
            out = f"""• <b>Eval-GCC</b>\n{_match}\n\n• <b>ERROR:</b>\n"""
            out += u._html(m[1], "")
            await msg.edit(out, parse_mode="html")
        else:
            out = f"• Eval-GCC:\n{match} \n\n\n• ERROR:\n{m[1]}"
            with BytesIO(out.encode()) as out_file:
                out_file.name = "compile-error-gcc.txt"
                caption = "<b>• Eval-GCC:</b>\n" + u._html(
                    match if len(match) < 610 else match[:600] + " ...", "c"
                )
                await e.client.send_file(
                    e.chat_id,
                    out_file,
                    force_document=True,
                    thumb=ULTConfig.thumb,
                    allow_cache=False,
                    caption=caption,
                    parse_mode="html",
                    reply_to=e.reply_to_msg_id,
                )
            await msg.delete()
        return osremove("ultroid.c", "ultroid.out")

    time_t = time.perf_counter()
    stdout, err = await bash("./ultroid.out")
    _time = (time.perf_counter() - time_t) * 1000
    _tfime = time_formatter(_time)
    time_t = _tfime if not _tfime == "0s" else f"{_time:.3f}ms"

    if len(match + str(stdout) + str(err)) > 3000:
        out = f"• Eval-GCC: ({time_t})\n{match} \n\n\n"
        if stdout != "":
            out += f"• OUTPUT:\n{stdout}\n\n\n"
        if err:
            out += f"• ERROR:\n{err}"
        with BytesIO(out.encode()) as out_file:
            out_file.name = "gcc_output.txt"
            caption = "<b>• Eval-GCC:</b>\n" + u._html(
                match if len(match) < 610 else match[:600] + " ...", "c"
            )
            await e.client.send_file(
                e.chat_id,
                out_file,
                force_document=True,
                thumb=ULTConfig.thumb,
                allow_cache=False,
                caption=caption,
                parse_mode="html",
                reply_to=e.reply_to_msg_id,
            )
        await msg.delete()
    else:
        _match = u._html(match, "c")
        out = f"""• <b>Eval-GCC</b> (<i>{time_t}</i>)\n{_match}\n\n"""
        if stdout != "":
            out += f"• <b>OUTPUT:</b>\n"
            out += u._html(stdout, "") + "\n\n"
        if err:
            out += f"• <b>ERROR:</b>\n"
            out += u._html(err, "")
        await msg.edit(out, parse_mode="html")
    osremove("ultroid.c", "ultroid.out")
    await u._evalogger(match, e, "c")
