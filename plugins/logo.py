# Ultroid - UserBot
# Copyright (C) 2021-2023 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}logo <text>`
   Generate a logo of the given Text
   Or Reply To image , to write ur text on it.
   Or Reply To Font File, To write with that font.
"""

import glob
import os
import random

from telethon.tl.types import InputMessagesFilterPhotos

try:
    from PIL import Image
except ImportError:
    Image = None

from pyUltroid.fns.misc import unsplashsearch
from pyUltroid.fns.tools import LogoHelper

from . import (
    check_filename,
    download_file,
    get_string,
    inline_mention,
    mediainfo,
    osremove,
    ultroid_bot,
    ultroid_cmd,
)


@ultroid_cmd(pattern="logo( (.*)|$)")
async def logo_gen(event):
    xx = await event.eor(get_string("com_1"))
    name = event.pattern_match.group(2)
    if not name:
        return await xx.eor("`Give a name to Generate Logo!`", time=8)

    bg_, font_ = None, None
    if event.reply_to_msg_id:
        temp = await event.get_reply_message()
        if temp.media:
            if hasattr(temp.media, "document") and (
                ("font" in temp.file.mime_type)
                or any(i in temp.file.name for i in (".ttf", ".otf"))
            ):
                font_ = await temp.download_media("resources/fonts/")
            elif "pic" in mediainfo(temp.media):
                bg_ = await temp.download_media()

    if not font_:
        fpath_ = glob.glob("resources/fonts/*")
        font_ = random.choice(fpath_)
    if not bg_:
        SRCH = (
            "background",
            "neon",
            "anime",
            "art",
            "bridges",
            "streets",
            "computer",
            "cyberpunk",
            "nature",
            "abstract",
            "exoplanet",
            "magic",
            "3d render",
        )
        res = await unsplashsearch(random.choice(SRCH), limit=1)
        bg_, _ = await download_file(
            res[0], check_filename("resources/downloads/unsplash_temp.png")
        )
        newimg = check_filename("resources/downloads/unsplash_temp_jpg.jpg")
        img_ = Image.open(bg_)
        img_.save(newimg, optimize=True, quality=85)
        osremove(bg_)
        bg_ = newimg

    if len(name) <= 8:
        strke = 10
    elif len(name) >= 9:
        strke = 5
    else:
        strke = 20
    name = LogoHelper.make_logo(
        bg_,
        name,
        font_,
        fill="white",
        stroke_width=strke,
        stroke_fill="black",
    )
    # await xx.edit("`Done!`")
    await event.respond(
        f"Logo by {inline_mention(ultroid_bot.me)}!",
        file=name,
        force_document=True,
    )
    osremove(name, bg_)
    await xx.delete()
