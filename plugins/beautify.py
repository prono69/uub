# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("help_beautify")


import asyncio
import random

from telethon.utils import get_display_name

from pyUltroid.custom.functions import RaySoThemes
from . import (
    LOGS,
    Carbon,
    _get_colors,
    asyncread,
    get_string,
    generate_rayso,
    inline_mention,
    mediainfo,
    osremove,
    unix_parser,
    ultroid_cmd,
)


@ultroid_cmd(
    pattern=r"(r)?carbon( ([\s\S]*)|$)",
)
async def crbn(event):
    msg = await event.eor(get_string("com_1"))
    te = event.pattern_match.group(1)
    code = event.pattern_match.group(3)
    reply_to = event.reply_to_msg_id or event.id
    all_colors = await _get_colors(pick=False)
    col = random.choice(all_colors)  # if te[0] == "r" else "White"
    if not code and event.reply_to:
        temp = await event.get_reply_message()
        if (
            temp.media
            and mediainfo(temp.media) == "document"
            and temp.file.size < 10 * 1024 * 1024
        ):
            dl = await temp.download_media()
            try:
                code = await asyncread(dl)
            except Exception as exc:
                return await msg.edit(f"**Error:**  `{exc}`")
            finally:
                osremove(dl)
        elif temp.text:
            code = temp.message

    if not code:
        return await msg.eor(get_string("carbon_2"))

    xx = await Carbon(code=code, file_name="ultroid_carbon", backgroundColor=col)
    if isinstance(xx, dict):
        return await msg.edit(f"`{xx}`")

    mention = inline_mention(event.sender or await event.get_sender())
    caption = f"Carbonised by {mention}"
    await asyncio.gather(
        msg.try_delete(),
        event.respond(caption, file=xx, reply_to=reply_to),
    )


@ultroid_cmd(
    pattern="ccarbon( (.*)|$)",
)
async def custom_crbn(event):
    match = event.pattern_match.group(2)
    if not match:
        return await event.eor(get_string("carbon_3"))

    msg = await event.eor(get_string("com_1"))
    code, reply_to = "", event.reply_to_msg_id or event.id

    if event.reply_to_msg_id:
        temp = await event.get_reply_message()
        if (
            temp.media
            and mediainfo(temp.media) == "document"
            and temp.file.size < 10 * 1024 * 1024
        ):
            dl = await temp.download_media()
            try:
                code = await asyncread(dl)
            except Exception as exc:
                return await msg.edit(f"**Error:**  `{exc}`")
            finally:
                osremove(dl)
        elif temp.text:
            code = temp.message
    else:
        if match == "list":
            return await msg.edit(
                f"[List of All Carbon Themes!](https://graph.org/Ultroid-09-13-11)"
            )

        try:
            match, code = match.split(" ", maxsplit=1)
            if not code:
                raise TypeError
        except Exception:
            LOGS.exception("ccarbon error")
            return await msg.eor(get_string("carbon_2"))

    xx = await Carbon(code=code, backgroundColor=match)
    if isinstance(xx, dict):
        return await msg.edit(f"`{xx}`")

    mention = inline_mention(event.sender or await event.get_sender())
    caption = f"Carbonised by {mention}"
    await asyncio.gather(
        event.respond(caption, file=xx, reply_to=reply_to),
        msg.try_delete(),
    )


@ultroid_cmd(
    pattern=r"rayso( ([\s\S]*)|$)",
)
async def rayso_on(ult):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return await ult.eor(
            "`playwright` is not installed!\nPlease install it to use this command.."
        )

    msg = await ult.eor(get_string("com_1"))
    args = unix_parser(ult.pattern_match.group(2) or "")
    text, title = args.args, get_display_name(ult.chat)
    reply_to = ult.reply_to_msg_id or ult.id

    if not text and ult.reply_to:
        reply = await ult.get_reply_message()
        title = get_display_name(reply.sender)
        if (
            reply.media
            and mediainfo(reply.media) == "document"
            and reply.file.size < 10 * 1024 * 1024
        ):
            dl = await reply.download_media()
            try:
                text = await asyncread(dl)
            except Exception as exc:
                return await msg.edit(f"**Error:**  `{exc}`")
            finally:
                osremove(dl)
        elif reply.text:
            text = reply.message

    if not text:
        return await msg.eor(
            f"`Gimme text or Reply to message to make Rayso..`", time=6
        )

    dark_mode = bool(args.kwargs.get("d", 1))
    theme = args.kwargs.get("th", random.choice(RaySoThemes))
    title = args.kwargs.get("ti", title)
    if text == "list":
        text = "**List of Rayso Themes:**\n" + "\n".join(
            [f"- `{th_}`" for th_ in RaySoThemes]
        )
        return await ult.edit(text)

    img = await generate_rayso(
        text=text,
        title=title,
        theme=theme,
        dark_mode=dark_mode,
    )
    if isinstance(img, str):
        mention = inline_mention(ult.sender or await ult.get_sender(), html=True)
        caption = f"<blockquote>Theme Used - {theme}\nDark Mode - {dark_mode}</blockquote>\n\n<b>Rayso by {mention}</b>"
        await asyncio.gather(
            ult.respond(caption, file=img, reply_to=reply_to, parse_mode="html"),
            msg.try_delete(),
        )
        osremove(img)
