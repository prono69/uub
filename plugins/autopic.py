# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from pathlib import Path
from random import choice

from telethon.tl.functions.photos import UploadProfilePhotoRequest

from pyUltroid.custom.bing_image import BingScrapper

from . import (
    LOGS,
    osremove,
    get_help,
    get_string,
    scheduler,
    udB,
    ultroid_bot,
    ultroid_cmd,
)


__doc__ = get_help("help_autopic")


async def get_or_fetch_image(autopic_dir):
    diriter = lambda p: list(p.iterdir())
    autopic_dir = Path(autopic_dir)
    if not (autopic_dir.is_dir() and (pics := diriter(autopic_dir))):
        query = autopic_dir.name.lstrip("bing-")
        bing = BingScrapper(query=query, limit=250, filter="photo")
        autopic_dir = await bing.download()
        udB.set_key("AUTOPIC", autopic_dir)
        pics = diriter(Path(autopic_dir))
    return str(choice(pics))


async def autopic_func():
    if not (autopic_dir := udB.get_key("AUTOPIC")):
        return
    try:
        path = await get_or_fetch_image(autopic_dir)
    except Exception as exc:
        return LOGS.exception(f"Autopic Error: {exc}")
    try:
        tg_file = await ultroid_bot.upload_file(path)
        await ultroid_bot(UploadProfilePhotoRequest(file=tg_file))
        osremove(path)
    except Exception as exc:
        LOGS.warning(f"autopic error in {path}: {exc}")


@ultroid_cmd(pattern="autopic( (.*)|$)")
async def autopic(e):
    search = e.pattern_match.group(2)
    autopic_dir = udB.get_key("AUTOPIC")
    if autopic_dir and (not search or search == "stop"):
        udB.del_key("AUTOPIC")
        osremove(autopic_dir, folders=True)
        if scheduler:
            scheduler.remove_job("autopic")
        return await e.eor(get_string("autopic_5"))

    if not search:
        return await e.eor(get_string("autopic_1"), time=6)

    if not scheduler:
        return await e.eor("`APScheduler is missing, Can't Use Autopic`", time=6)

    eris = await e.eor(get_string("com_1"))
    try:
        path = await get_or_fetch_image(f"resources/downloads/bing-{search}")
    except Exception as exc:
        LOGS.exception(f"Autopic Error: {exc}")
        return await eris.eor(get_string("autopic_2").format(search), time=10)

    udB.set_key("AUTOPIC", str(Path(path).parent))
    await eris.edit(get_string("autopic_3").format(search))
    sleep = udB.get_key("SLEEP_TIME") or 1221
    scheduler.add_job(
        autopic_func,
        trigger="interval",
        seconds=sleep,
        id="autopic",
        jitter=60,
    )


if udB.get_key("AUTOPIC"):
    sleep = udB.get_key("SLEEP_TIME") or 1221
    if scheduler:
        scheduler.add_job(
            autopic_func,
            "interval",
            seconds=sleep,
            id="autopic",
            jitter=60,
        )
    else:
        LOGS.error(f"autopic: 'apscheduler' is not installed.")
