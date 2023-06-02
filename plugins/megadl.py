# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

•{i}megadl <link>
  It Downloads and Upload Files from mega.nz Links.
"""

from pathlib import Path
from time import time

from . import (
    HNDLR,
    LOGS,
    bash,
    check_filename,
    get_all_files,
    get_string,
    time_formatter,
    ultroid_cmd,
    random_string,
)


@ultroid_cmd(pattern="megadl( (.*)|$)")
async def megadl(e):
    link = e.pattern_match.group(2)
    tmp_dir = check_filename(f"mega/{random_string(9).lower()}")
    Path(tmp_dir).mkdir(parents=True)
    xx = await e.eor(f"{get_string('com_1')}\nTo Check Progress: `{HNDLR}ls {tmp_dir}`")

    s_time = time()
    out, err = await bash(f"megadl {link} --path {tmp_dir}")
    if err:
        LOGS.warning(err)

    time_taken = time_formatter((time() - s_time) * 1000)
    total_files = len(get_all_files(tmp_dir))
    final_msg = "**Downloaded {total} files in {time}!** \n\n**Directory:** `{dir}`"
    await xx.reply(final_msg.format(total=total_files, time=time_taken, dir=tmp_dir))
