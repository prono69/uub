# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}compress <reply to video/path>`
    Available Flags -
    crf: -c=28
    codec: -x264
    speed: -s=superfast
    others: -r > to fix resolution and fps
"""

import asyncio
from math import floor
from pathlib import Path
from re import findall
from shlex import quote
from time import time

from telethon.errors.rpcerrorlist import MessageNotModifiedError, MessageIdInvalidError

from pyUltroid.custom._transfer import pyroDL, pyroUL
from . import (
    LOGS,
    asyncread,
    asyncwrite,
    bash,
    check_filename,
    gen_mediainfo,
    get_string,
    humanbytes,
    mediainfo,
    osremove,
    time_formatter,
    ultroid_cmd,
    unix_parser,
)


FFMPEG_CMD = "ffmpeg -hide_banner -loglevel error -progress {progress_file} -i {input_file} -preset {speed} -vcodec {codec} -crf {crf} {other_cmds} {audio_cmd} -c:s copy {output_file} -y"


def fix_resolution(width, height):
    fix_by4 = lambda n: n - (n % 4)
    # for landscape or portrait
    new_height = 720 if width >= height else 1280
    if height > new_height:
        width = fix_by4(round(width / (height / new_height)))
        height = new_height
    else:
        width, height = fix_by4(width), fix_by4(height)
    return width, height


@ultroid_cmd(pattern="compress( (.*)|$)")
async def og_compressor(e):
    msg = await e.eor("`Checking...`")
    args = e.pattern_match.group(2)
    args = unix_parser(args or "")
    vido = await e.get_reply_message()

    # _ext = "mkv"
    _audio_cmd = "-c:a copy"
    _codec = "libx264" if args.kwargs.pop("x264", 0) else "libx265"
    _crf = args.kwargs.pop("c", 28 if _codec == "libx265" else 35)
    _speed = args.kwargs.pop("s", "ultrafast")

    if not vido and args.args:
        path = Path(args.args)
        if not path.is_file():
            return await msg.edit("`Path not found...`")
        to_delete, reply_to = False, e.id
        await msg.edit(f"`Found Path {str(path)}\n\nNow Compressing...`")

    elif (vido and vido.media) and mediainfo(vido.media).startswith(("video", "gif")):
        await msg.edit(get_string("audiotools_5"))
        dlx = pyroDL(event=msg, source=vido)
        path = await dlx.download(_log=False, auto_edit=False, **args.kwargs)
        if isinstance(path, Exception):
            return await msg.edit("#Error in downloading file: `{path}`")
        path = Path(path)
        to_delete, reply_to = True, vido.id
        await msg.edit(
            f"`Downloaded {str(path)} in {dlx.dl_time}... \n\nNow Compressing...`"
        )

    else:
        return await msg.eor(get_string("audiotools_8"), time=8)

    _other_cmd = ""
    old_edit_text = ""
    og_size = path.stat().st_size
    edit_sleep_time = 8.5  # if e.client._bot else 8
    out_path = check_filename("resources/downloads/" + path.stem + "-compressed.mp4")
    minfo = await gen_mediainfo(str(path))
    total_frame = minfo.get("frames")
    if minfo.get("type") == "gif" or path.suffix.lower() == ".gif":
        _audio_cmd = ""
        _codec = "libx264"

    # x, y = await bash(f'''mediainfo --fullscan {quote(path)} | grep "Frame count"''')
    # total_frame = x.split(":")[1].split("\n")[0]

    progress_file = f"progress-{time()}.txt"
    Path(progress_file).touch()
    if args.kwargs.pop("r", 0):
        if total_frame and (total_frame / minfo.get("duration")) > 31:
            _other_cmd += "-r 30 "
            total_frame = round(minfo.get("duration") * 30.5)
        width, height = fix_resolution(minfo.get("width"), minfo.get("height"))
        _other_cmd += f"-vf scale=w={width}:h={height}"

    pre_time = time()
    ffmpeg = await asyncio.create_subprocess_shell(
        FFMPEG_CMD.format(
            progress_file=quote(progress_file),
            input_file=quote(str(path)),
            crf=str(_crf),
            output_file=quote(out_path),
            codec=_codec,
            speed=_speed,
            audio_cmd=_audio_cmd,
            other_cmds=_other_cmd,
        ),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Starting Compress!
    sleep_time_count = 0
    while type(ffmpeg.returncode) != int:
        speed = 0
        await asyncio.sleep(edit_sleep_time)
        sleep_time_count += edit_sleep_time
        filetext = await asyncread(progress_file)
        await asyncwrite(progress_file, filetext[-350:], mode="w")
        compressed_frames = findall("frame=(\\d+)", filetext)
        compressed_size = findall("total_size=(\\d+)", filetext)
        del filetext

        edit_text = [f"`Compressing {Path(out_path).name} at {_crf} CRF` "]
        if total_frame and compressed_frames:
            compressed_size = int(compressed_size[-1]) if compressed_size else 0
            compressed_frames = int(compressed_frames[-1]) if compressed_frames else 0
            compressed_percent = compressed_frames * 100 / total_frame
            time_diff = time() - pre_time
            speed = round(compressed_frames / time_diff, 2)
            if int(speed) != 0:
                some_eta = ((total_frame - compressed_frames) / speed) * 1000
                edit_text.append(
                    "`[{0}{1}] {2}%` \n".format(
                        "".join("●" for i in range(floor(compressed_percent / 5))),
                        "".join("" for i in range(20 - floor(compressed_percent / 5))),
                        round(compressed_percent, 2),
                    )
                )
                edit_text.append(f"**Done ~**  `{humanbytes(compressed_size)}` ")
                edit_text.append(f"**ETA ~**  `{time_formatter(some_eta)}`")
        if len(edit_text) <= 1:
            if compressed_size:
                compressed_size = humanbytes(int(compressed_size[-1]))
            else:
                try:
                    compressed_size = Path(out_path).stat().st_size
                except FileNotFoundError:
                    compressed_size = 0
            edit_text = (
                f"{edit_text}\n` ~ Missing Frame Counts..` \n\n"
                f"{compressed_size}**Elapsed ~**  `{time_formatter(sleep_time_count * 1000)}`"
            )
            edit_sleep_time = 15

        edit_text = "\n".join(edit_text)
        if int(speed) > 0 and old_edit_text != edit_text:
            try:
                await msg.edit(edit_text)
                old_edit_text = edit_text
            except MessageNotModifiedError:
                LOGS.debug("Error in Compressor progress..", exc_info=True)
            except MessageIdInvalidError:
                await asyncio.sleep(3)
                try:
                    ffmpeg.kill()
                except:
                    pass
                await asyncio.sleep(5)
                osremove(progress_file, out_path)
                if to_delete:
                    osremove(path)
                return LOGS.debug(f"cancelled compression of: {path}")

    # Uploader
    if to_delete:
        osremove(path)
    osremove(progress_file)
    time_diff = time_formatter((time() - pre_time) * 1000)

    minfo = await gen_mediainfo(out_path)
    if minfo.get("type") == "video" and not minfo.get("has_audio"):
        o_path = Path(out_path)
        out_path = check_filename(o_path.with_suffix(".mkv"))
        o_path.rename(out_path)

    compress_size = Path(out_path).stat().st_size
    await msg.edit(
        f"`Compressed {humanbytes(og_size)} to {humanbytes(compress_size)} in {time_diff}\nTrying to Upload...`"
    )
    size_diff = 100 - ((compress_size / og_size) * 100)

    edit_text = f"{minfo.get('width')}x{minfo.get('height')}p"
    if frames := minfo.get("frames"):
        edit_text += f" ~ {round(frames / minfo.get('duration'))}fps"
    caption = (
        f"**Compressed from** `{humanbytes(og_size)}` **to** `{humanbytes(compress_size)}` **in** `{time_diff}`\n\n"
        f"**Codec:** `{_codec}`\n"
        f"**Resolution:** `{edit_text}`\n"
        f"**Compression Ratio:** `{size_diff:.2f}%`"
    )
    x = pyroUL(event=msg, _path=out_path)
    await x.upload(
        caption=caption,
        delete_file=True,
        reply_to=reply_to,
        _log=False,
        **args.kwargs,
    )
