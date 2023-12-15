# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}saavn <search query>`
    Download songs from Saavn.

• `{i}google <query>`
    For doing google search.

• `{i}github <username>`
    Get full information of the users github profile.

• `{i}img <query>`
  `{i}img <query> ; <no of results>`
    For doing Images search.

• `{i}reverse`
    Reply an Image or sticker to find its sauce.
"""

import requests
from bs4 import BeautifulSoup as bs
from telethon.tl.types import DocumentAttributeAudio

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import cv2
except ImportError:
    cv2 = None

from pyUltroid.fns.misc import google_search
from pyUltroid.fns.tools import get_google_images, saavn_search
from pyUltroid.custom.reverse_search import GoogleReverseSearch

from . import (
    LOGS,
    async_searcher,
    con,
    eod,
    fast_download,
    get_string,
    osremove,
    string_is_url,
    ultroid_cmd,
)


@ultroid_cmd(
    pattern="github( (.*)|$)",
)
async def gitsearch(event):
    usrname = event.pattern_match.group(2)
    if not usrname:
        return await event.eor(get_string("srch_1"))
    url = f"https://api.github.com/users/{usrname}"
    ult = await async_searcher(url, re_json=True)
    try:
        uname = ult["login"]
        uid = ult["id"]
        upic = f"https://avatars.githubusercontent.com/u/{uid}"
        ulink = ult["html_url"]
        uacc = ult["name"]
        ucomp = ult["company"]
        ublog = ult["blog"]
        ulocation = ult["location"]
        ubio = ult["bio"]
        urepos = ult["public_repos"]
        ufollowers = ult["followers"]
        ufollowing = ult["following"]
    except BaseException:
        return await event.eor(get_string("srch_2"))
    fullusr = f"""
**[GITHUB]({ulink})**
**Name** - {uacc}
**UserName** - {uname}
**ID** - {uid}
**Company** - {ucomp}
**Blog** - {ublog}
**Location** - {ulocation}
**Bio** - {ubio}
**Repos** - {urepos}
**Followers** - {ufollowers}
**Following** - {ufollowing}
"""
    await event.respond(fullusr, file=upic)
    await event.delete()


@ultroid_cmd(
    pattern="google( (.*)|$)",
    manager=True,
)
async def google(event):
    inp = event.pattern_match.group(1).strip()
    if not inp:
        return await eod(event, get_string("autopic_1"))
    x = await event.eor(get_string("com_2"))
    gs = await google_search(inp)
    if not gs:
        return await eod(x, get_string("autopic_2").format(inp))
    out = ""
    for res in gs:
        text = res["title"]
        url = res["link"]
        des = res["description"]
        out += f" 👉🏻  [{text}]({url})\n`{des}`\n\n"
    omk = f"**Google Search Query:**\n`{inp}`\n\n**Results:**\n{out}"
    await x.eor(omk, link_preview=False)


@ultroid_cmd(pattern="img( (.*)|$)")
async def goimg(event):
    query = event.pattern_match.group(2)
    if not query:
        return await event.eor(get_string("autopic_1"))
    nn = await event.eor(get_string("com_1"))
    lmt = 5
    if ";" in query:
        try:
            lmt = int(query.split(";")[1])
            query = query.split(";")[0]
        except BaseException:
            pass
    images = await get_google_images(query)
    for img in images[:lmt]:
        try:
            await event.client.send_file(event.chat_id, file=img["original"])
        except Exception as er:
            LOGS.exception(er)
    await nn.delete()


@ultroid_cmd(pattern="reverse( (.*)|$)")
async def reverse(event):
    target = None
    args = event.pattern_match.group(2)
    ult = await event.eor(get_string("com_1"))
    if args and string_is_url(args):
        target = args
    elif event.reply_to:
        reply = await event.get_reply_message()
        if reply.media:
            dl = await reply.download_media()
            target = await con.convert(dl, convert_to="png")
    if not target:
        return await ult.eor("`Reply to an Image or give a URL..`", time=8)

    try:
        response = await GoogleReverseSearch.init(target, similar_results=False)
        if not (response and (response := response.get("match"))):
            return await ult.edit(f"`Could not find any result..`")

        title, link, info, page = (
            response.get("title"),
            response.get("search_url"),
            response.get("info"),
            response.get("page_url"),
        )
        result = f"[{title}]({link})" if link else f"`{title}`"
        if info:
            result += f"  -  `{info}`"
        if page:
            result += f"\n\n**URL** - {page}"
        await ult.edit(f"`Got Results for this Image >>>`\n\n**Sauce:**  {result}")
    except Exception as exc:
        LOGS.exception(exc)
        await ult.edit(f"**Error:**  `{exc}`")
    finally:
        if event.reply_to:
            osremove(target, dl)


@ultroid_cmd(
    pattern="saavn( (.*)|$)",
)
async def siesace(e):
    song = e.pattern_match.group(1).strip()
    if not song:
        return await e.eor("`Give me Something to Search", time=5)
    eve = await e.eor(f"`Searching for {song} on Saavn...`")
    try:
        data = (await saavn_search(song))[0]
    except IndexError:
        return await eve.eor(f"`{song} not found on saavn.`")
    try:
        title = data["title"]
        url = data["url"]
        img = data["image"]
        duration = data["duration"]
        performer = data["artists"]
    except KeyError:
        return await eve.eor("`Something went wrong.`")
    song, _ = await fast_download(url, filename=f"{title}.m4a")
    thumb, _ = await fast_download(img, filename=f"{title}.jpg")
    song, _ = await e.client.fast_uploader(song, to_delete=True)
    await eve.eor(
        file=song,
        text=f"`{title}`\n`From Saavn`",
        attributes=[
            DocumentAttributeAudio(
                duration=int(duration),
                title=title,
                performer=performer,
            )
        ],
        supports_streaming=True,
        thumb=thumb,
    )
    osremove(thumb)
    await eve.delete()
