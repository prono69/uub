# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

•{i}megadl <link>
  It Downloads and Upload Files from mega.nz links.
"""

from datetime import datetime

from . import (
    HNDLR,
    LOGS,
    bash,
    get_string,
    humanbytes,
    os,
    time_formatter,
    ultroid_cmd,
    random_string,
)


@ultroid_cmd(pattern="megadl( (.*)|$)")
async def megadl(e):
    link = e.pattern_match.group(1).strip()
    _dir = f"mega/{random_string(7).lower()}"
    os.makedirs(_dir)
    s = datetime.now()
    xx = await e.eor(f"{get_string('com_1')}\nTo Check Progress: `{HNDLR}ls {_dir}`")
    x, y = await bash(f"megadl {link} --path {_dir}")

    if y:
        LOGS.exception(y)
    tm = (datetime.now() - s).seconds
    # await xx.edit("`Done`")
    await xx.reply(
        f"**Downloaded all files in {tm}s!** \n\n**Directory:** `{_dir}`",
    )
