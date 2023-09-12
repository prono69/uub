# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("help_beautify")


import asyncio
import os
import random

from telethon.utils import get_display_name

from . import asyncread, Carbon, get_string, inline_mention, ultroid_cmd


_colorspath = "resources/colorlist.txt"

if os.path.exists(_colorspath):
    with open(_colorspath, "r") as f:
        all_col = f.read().splitlines()
else:
    all_col = []


@ultroid_cmd(
    pattern="(rc|c)arbon",
)
async def crbn(event):
    xxxx = await event.eor(get_string("com_1"))
    te = event.pattern_match.group(1)
    col = random.choice(all_col)  # if te[0] == "r" else "White"
    if event.reply_to_msg_id:
        temp = await event.get_reply_message()
        if temp.media:
            b = await event.client.download_media(temp)
            with open(b) as a:
                code = a.read()
            os.remove(b)
        else:
            code = temp.message
    else:
        try:
            code = event.text.split(" ", maxsplit=1)[1]
        except IndexError:
            return await xxxx.eor(get_string("carbon_2"))
    xx = await Carbon(code=code, file_name="ultroid_carbon", backgroundColor=col)
    if isinstance(xx, dict):
        return await xxxx.edit(f"`{xx}`")
    await xxxx.delete()
    await event.reply(
        f"Carbonised by {inline_mention(event.sender)}",
        file=xx,
    )


@ultroid_cmd(
    pattern="ccarbon( (.*)|$)",
)
async def crbn(event):
    match = event.pattern_match.group(1).strip()
    if not match:
        return await event.eor(get_string("carbon_3"))

    msg = await event.eor(get_string("com_1"))
    if event.reply_to_msg_id:
        temp = await event.get_reply_message()
        if temp.media:
            b = await event.client.download_media(temp)
            code = await asyncread(b)
            os.remove(b)
        else:
            code = temp.message
    else:
        try:
            match = match.split(" ", maxsplit=1)
            code = match[1]
            match = match[0]
        except IndexError:
            return await msg.eor(get_string("carbon_2"))
    xx = await Carbon(code=code, backgroundColor=match)
    await asyncio.gather(
        msg.delete(),
        event.respond(
            f"Carbonised by {inline_mention(event.sender)}",
            file=xx,
            reply_to=msg.reply_to_msg_id,
        ),
    )


RaySoTheme = (
    "meadow",
    "breeze",
    "raindrop",
    "candy",
    "crimson",
    "falcon",
    "sunset",
    "midnight",
)


@ultroid_cmd(pattern="rayso")
async def pass_on(ult):
    spli = ult.text.split()
    msg = await ult.eor(get_string("com_1"))
    theme, dark, title, text = None, True, get_display_name(ult.chat), None
    if len(spli) > 2:
        if spli[1] in RaySoTheme:
            theme = spli[1]
        dark = spli[2].lower().strip() in ["true", "t"]
    elif len(spli) > 1:
        if spli[1] in RaySoTheme:
            theme = spli[1]
        elif spli[1] == "list":
            text = "**List of Rayso Themes:**\n" + "\n".join(
                [f"- `{th_}`" for th_ in RaySoTheme]
            )
            return await ult.eor(text)
        else:
            try:
                text = ult.text.split(maxsplit=1)[1]
            except IndexError:
                pass

    if not theme:
        theme = random.choice(RaySoTheme)
    if ult.is_reply:
        msg = await ult.get_reply_message()
        text = msg.message
        title = get_display_name(msg.sender)

    img = await Carbon(text, rayso=True, title=title, theme=theme, darkMode=dark)
    caption = f"Rayso '{theme}' by {inline_mention(ult.sender)}"
    await asyncio.gather(
        ult.respond(caption, file=img, reply_to=msg.reply_to_msg_id),
        msg.delete(),
    )
