# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available

• `{i}invertgif`
  Make Gif Inverted(negative).

• `{i}bwgif`
  Make Gif black and white

• `{i}rvgif`
  Reverse a gif

• `{i}vtog`
  Reply To Video , It will Create Gif
  Video to Gif

• `{i}gif <query>`
   Send video regarding to query.
"""

import random
from shlex import quote

from . import (
    HNDLR,
    LOGS,
    bash,
    check_filename,
    genss,
    get_string,
    mediainfo,
    osremove,
    tg_downloader,
    ultroid_cmd,
)


@ultroid_cmd(pattern="(bw|invert)gif$")
async def igif(e):
    match = e.pattern_match.group(1).strip()
    a = await e.get_reply_message()
    if not (a and a.media and "gif" in mediainfo(a.media)):
        return await e.eor("`Reply To gif only`", time=5)

    xx = await e.eor(get_string("com_1"))
    z = await a.download_media()
    out = check_filename("ult.gif")
    if match == "bw":
        cmd = f"ffmpeg -i {quote(z)} -vf format=gray {quote(out)} -y"
    else:
        cmd = f'ffmpeg -i {quote(z)} -vf lutyuv="y=negval:u=negval:v=negval" {quote(out)} -y'
    try:
        await bash(cmd)
        await e.client.send_file(e.chat_id, out, supports_streaming=True)
        await xx.delete()
    except Exception as exc:
        LOGS.info(exc)
    finally:
        osremove(z, out)


@ultroid_cmd(pattern="rvgif$")
async def reverse_gif(event):
    a = await event.get_reply_message()
    if not (a and a.media and "video" in mediainfo(a.media)):
        return await event.eor("`Reply To Video only`", time=5)

    msg = await event.eor(get_string("com_1"))
    file = await a.download_media()
    out = check_filename("reversed.mp4")
    try:
        await bash(f"ffmpeg -i {quote(file)} -vf reverse -af areverse {quote(out)} -y")
        await event.respond("- **Reversed Video/GIF**", file=out)
    except Exception as exc:
        LOGS.info(exc)
    finally:
        osremove(out, file)
        await msg.delete()


@ultroid_cmd(pattern="gif( (.*)|$)")
async def gifs(ult):
    get = ult.pattern_match.group(1).strip()
    xx = random.randint(0, 5)
    n = 0
    if ";" in get:
        try:
            n = int(get.split(";")[-1])
        except IndexError:
            pass
    if not get:
        return await ult.eor(f"`{HNDLR}gif <query>`")
    m = await ult.eor(get_string("com_2"))
    gifs = await ult.client.inline_query("gif", get)
    if not n:
        await gifs[xx].click(
            ult.chat_id, reply_to=ult.reply_to_msg_id, silent=True, hide_via=True
        )
    else:
        for x in range(n):
            await gifs[x].click(
                ult.chat_id, reply_to=ult.reply_to_msg_id, silent=True, hide_via=True
            )
    await m.delete()


@ultroid_cmd(pattern="vtog$")
async def vtogif(e):
    a = await e.get_reply_message()
    if not (a and a.media and "video" in mediainfo(a.media)):
        return await e.eor("`Reply To video only`", time=5)

    xx = await e.eor(get_string("com_1"))
    out = check_filename("videotogif.gif")
    z, _ = await tg_downloader(media=a, event=xx, show_progress=True)
    dur = await genss(z)
    if int(dur) < 120:
        await bash(
            f'ffmpeg -i {quote(z)} -vf "fps=10,scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 {quote(out)} -y'
        )
    else:
        await bash(
            f'ffmpeg -ss 3 -t 100 -i {quote(z)} -vf "fps=10,scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 {quote(out)} -y'
        )

    try:
        await e.client.send_file(e.chat_id, out, support_streaming=True)
    except Exception as exc:
        LOGS.info(exc)
    finally:
        osremove(z, out)
        await xx.delete()
