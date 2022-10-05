# PyroGram Download and Upload.
# Written by (@ah3h3,  @spemgod) for fast upload and downloads.
#
# Edited on 21-07-2022:
#  - created class pyroUL
#  - changed lots of helper functions.
#  - added pyroDL on 23-07-22
#  - fixed for 0.7: 06-09-22
#  - overhaul 0.7.1: 06-10-22

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import asyncio
from math import floor
from time import time
from io import BytesIO
from PIL import Image, ImageFilter
from random import choice, random_string
from os import path, remove, rename, walk, getcwd

# from mimetypes import guess_all_extensions
from music_tag import load_file
from telethon.utils import get_display_name
from telethon.errors import MessageNotModifiedError, MessageIdInvalidError

from .helper import bash, time_formatter, inline_mention, cleargif, msg_link
from .tools import media_info, check_filename, humanbytes, shq
from .. import LOGS, udB, ultroid_bot, asst


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DUMP_CHANNEL = udB.get_key("TAG_LOG")
PROGRESS_LOG = {}
LOGGER_MSG = "Uploading {} | Path: {} | DC: {} | Size: {}"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Progress Bar
async def pyro_progress(
    current,
    total,
    message,
    edit_text,
    started_at,
    client=None,
    edit_delay=8,
    is_cancelled=False,
):
    if is_cancelled and client:
        client.stop_transmission()
        return
    jost = str(message.chat_id) + "_" + str(message.id)
    plog = PROGRESS_LOG.get(jost)
    now = time()
    if plog and current != total:
        if (now - plog) < edit_delay:
            return
    diff = now - started_at
    percentage = current * 100 / total
    speed = current / diff
    time_to_completion = round((total - current) / speed) * 1000
    progress_str = "`[{0}{1}] {2}%`\n\n".format(
        "".join("●" for i in range(floor(percentage / 5))),
        "".join("" for i in range(20 - floor(percentage / 5))),
        round(percentage, 2),
    )
    to_edit = f"✦ {edit_text} \n\n{progress_str}"
    to_edit += "`{0} of {1}`\n\n`✦ Speed: {2}/s`\n\n`✦ ETA: {3}`\n\n".format(
        humanbytes(current),
        humanbytes(total),
        humanbytes(speed),
        time_formatter(time_to_completion),
    )
    try:
        PROGRESS_LOG.update({jost: now})
        await message.edit(to_edit)
    except MessageNotModifiedError as exc:
        LOGS.exception(exc)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class pyroDL:
    def __init__(self, event, source, show_progress=True):
        self._cancelled = False
        self.event = event
        self.source = source
        self.show_progress = show_progress

    def updateAttrs(self, kwargs):
        self.filename = self.get_filename(self.msg)
        self.schd_delete = False
        self.auto_edit = True
        self.delay = 8
        self._log = True
        if self.show_progress:
            self.progress = pyro_progress
            self.progress_text = f"`Downloading {self.filename}...`"
        if list(filter(bool, [kwargs.pop(i, None) for i in ("schd_delete", "df")])):
            self.schd_delete = True
        for k, v in kwargs.items():
            setattr(self, k, v)

    async def copy_msg(self):
        try:
            return await self.source.copy(
                DUMP_CHANNEL,
                caption=f"#pyroDL\n\n{self.source.text}",
            )
        except BaseException as exc:
            LOGS.exception("pyroDL: err copying file: ")
            return f"Error copying file: `{exc}`"

    def getDC(self, file):
        if _dc := file.document:
            return _dc.dc_id
        return 1

    async def download(self, **kwargs):
        from pyrog import app

        _msg = await self.copy_msg()
        if type(_msg) == str:
            return await self.event.edit(_msg)
        await asyncio.sleep(0.75)
        self.dc = kwargs.pop("dc", self.getDC(_msg))
        self.client = app(self.dc)
        self.msg = await self.client.get_messages(DUMP_CHANNEL, _msg.id)
        self.updateAttrs(kwargs)
        dlx = await self.dls()
        if not self.auto_edit:
            return dlx
        if isinstance(dlx, Exception):
            await self.event.edit(f"Err in pyroDL: `{dlx}`")
        else:
            await self.event.edit(
                f"Successfully Downloaded \n`{dlx}` \nin {self.dl_time}",
            )

    async def dls(self):
        args = {"message": self.msg, "file_name": self.filename}
        if self._log:
            LOGS.debug(f"Downloading | [DC {self.dc}] | {self.filename}")
        if self.show_progress:
            prog_args = (
                self.event,
                self.progress_text,
                time(),
                self.client,
                self.delay,
                self._cancelled,
            )
            args.update({"progress": self.progress, "progress_args": prog_args})
        try:
            stime = time()
            dlx = await self.client.download_media(**args)
            self.dl_time = time_formatter((time() - stime) * 1000)
            return dlx
        except BaseException as exc:
            LOGS.exception("PyroDL err: ")
            return exc
        finally:
            if self.schd_delete:
                asst.loop.create_task(self.delTask(self.msg))

    @staticmethod
    async def delTask(task):
        await asyncio.sleep(8)
        await task.delete()

    @staticmethod
    def get_filename(event):
        def attrs(event, attr="file_name"):
            media_types = (
                "video",
                "photo",
                "document",
                "animation",
                "audio",
                "sticker",
            )
            for i in media_types:
                if mtype := getattr(event, i, None):
                    if attr := getattr(mtype, attr, None):
                        return attr

        _default = path.join(getcwd(), "resources/downloads/")
        if filename := attrs(event, "file_name"):
            return check_filename(path.join(_default, filename))
        return _default  # no filename, just a folder


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class pyroUL:
    def __init__(self, event, _path, show_progress=True):
        self.event = event
        self.show_progress = show_progress
        self.path = self.listFiles(_path)
        self.set_default_attributes()

    @staticmethod
    def listFiles(_path):
        if type(_path) in (list, tuple):
            return tuple(filter(lambda c: path.isfile(c), _path))
        elif path.isfile(_path):
            return (_path,)
        elif path.isdir(_path):
            col = []
            for dir, _, file in walk(_path):
                for _ in file:
                    col.append(path.join(dir, _))
            return tuple(col) if col else f"No files in this folder: `{_path}`"
        else:
            return f"Path doesn't exists: `{_path}`"

    # main functions

    def set_default_attributes(self):
        self._cancelled = False
        self.chat_id = DUMP_CHANNEL
        self.delete_file = False
        self.delete_thumb = True
        self.schd_delete = False
        self.auto_edit = True
        self.return_obj = False
        self.dc = 1
        self._log = True
        self.success = 0
        self.failed = 0
        self.silent = True
        self.force_document = False
        self.delay = 8  # progress edit delay

    async def upload(self, **kwargs):
        if type(self.path) == str:
            if self.event:
                await self.event.edit(self.path)
            return
        self.perma_attributes(kwargs)
        for count, file in enumerate(sorted(self.path), start=1):
            self.update_attributes(file, count)
            try:
                await self.pre_upload()
                ulfunc = self.uploader_func()
                out = await ulfunc()
                self.post_upload()
                if self.return_obj:
                    return out  # (for single file)
                await self.finalize(out)
                await self.handle_edits()
                await asyncio.sleep(self.sleeptime)
            except UploadError as exc:
                if _deleted := await self.handle_errors(exc):
                    return
                await asyncio.sleep(self.sleeptime)
                continue
        await self.do_final_edit()

    def perma_attributes(self, kwargs):
        from pyrog import app

        self.pre_time = time()
        self.client = app(self.dc)
        if self.show_progress:
            self.progress = pyro_progress
        e = self.event
        self.reply_to = getattr(e, "reply_to_msg_id", e.id) if e else None
        self.copy_to = e.chat_id if e else DUMP_CHANNEL
        for k, v in kwargs.items():
            setattr(self, k, v)
        if list(filter(bool, [kwargs.pop(i, None) for i in ("schd_delete", "df")])):
            self.schd_delete = True

    def update_attributes(self, file, count):
        self.file = file
        self.count = count
        if self.show_progress:
            self.progress_text = (
                f"__({self.count}/{len(self.path)})__ | ```Uploading {self.file}..```"
            )

    async def pre_upload(self):
        self.start_time = time()
        self.size_checks(self.file)
        await self.get_metadata()
        self.handle_webm()
        self.set_captions(pre=True)

    def uploader_func(self):
        type = self.metadata.get("type")
        if self.force_document:
            return self.document_uploader
        elif type == "video":
            return self.video_uploader
        elif type == "audio":
            return self.audio_uploader
        elif type == "image":
            return self.image_uploader
        elif type == "gif":
            return self.animation_uploader
        elif type == "sticker":
            return self.sticker_uploader
        else:
            return self.document_uploader

    def post_upload(self):
        self.ul_time = time_formatter((time() - self.start_time) * 1000)
        self.cleanups()
        self.set_captions()

    async def finalize(self, out):
        try:
            client = self.event.client if self.event else ultroid_bot
            await asyncio.sleep(1)
            file = await client.get_messages(out.chat.id, ids=out.id)
            if not (file and file.media):
                raise UploadError("Media not found // Error occurred in Uploading..")
            copy = await file.copy(
                self.copy_to,
                caption=self.caption,
                silent=self.silent,
                reply_to=self.reply_to,
            )
            asyncio.gather(self.dump_stuff(out, copy))
        except Exception as exc:
            er = "Error while copying file from DUMP: "
            LOGS.exception(er)
            raise UploadError(er)

    async def handle_edits(self):
        self.success += 1
        if self.auto_edit and self.event:
            await self.event.edit(
                f"__**Successfully Uploaded!  ({self.count}/{len(self.path)})**__ \n**>**  ```{self.file}```",
            )

    async def handle_errors(self, error):
        self.failed += 1
        if self.event and self.auto_edit:
            try:
                msg = f"__**Error While Uploading:**__ \n>  ```{self.file}``` \n>  `{error}`"
                await self.event.edit(msg)
            except MessageIdInvalidError:
                return True  # stop process..
            except Exception as exc:
                LOGS.exception("Error in editing Message..")

    async def do_final_edit(self):
        if len(self.path) > 1 and self.auto_edit and self.event:
            msg = f"__**Uploaded {self.success} files in {time_formatter((time() - self.pre_time) * 1000)}**__"
            if self.failed > 0:
                msg += f"\n\n**Got Error in {self.failed} files.**"
            await self.event.edit(msg)

    # Helper functions

    @staticmethod
    def size_checks(_path):
        size = path.getsize(_path)
        if size > 2097152000:
            raise UploadError("File Size is Greater than 2GB..")
        elif size == 0:
            raise UploadError("File Size = 0 B ...")

    async def get_metadata(self):
        self.metadata = media_info(self.file)
        type = self.metadata.get("type").lower()
        if not (self.force_document or hasattr(self, "thumb")):
            self.thumb = None
            if type == "video":
                self.thumb = await videoThumb(self.file, self.metadata["duration"])
            elif type == "audio":
                self.thumb = await audioThumb(self.file)
            elif type == "gif":
                self.thumb = await videoThumb(self.file, False)

    @property
    def sleeptime(self):
        _ = len(self.path)
        return 2 if _ in range(5) else (4 if _ < 25 else 8)

    def handle_webm(self):
        type = self.metadata.get("type")
        if type != "sticker" and self.file.lower().endswith(".webm"):
            ext = "" if self.file[:-5].lower().endswith((".mkv", ".mp4")) else ".mkv"
            new_pth = check_filename(self.file[:-5] + ext)
            rename(self.file, new_pth)
            self.file = new_pth

    def set_captions(self, pre=False):
        if pre:
            caption = getattr(self, "caption", None)
            self.pre_caption = caption if self.return_obj else None
            return
        if not hasattr(self, "caption"):
            self.caption = "__**Uploaded in {0}** • ({1})__ \n**>**  ```{2}```".format(
                self.ul_time,
                self.metadata["size"],
                self.file,
            )

    def cleanups(self):
        if self.delete_file:
            remove(self.file)
        if x := getattr(self, "thumb", None):
            if self.delete_thumb and "ultroid.jpg" not in x:
                remove(x)

    async def dump_stuff(self, upl, copy):
        await asyncio.sleep(0.5)
        await cleargif(copy)
        if self.schd_delete:
            await upl.delete()
        else:
            dumpCaption = "#PyroUL ~ {0} \n\n•  Chat:  [{1}]({2}) \n•  User:  {3} - {4} \n•  Path:  ```{5}```"
            sndr = copy.sender or await copy.get_sender()
            text = dumpCaption.format(
                f"{self.count}/{len(self.path)}",
                get_display_name(copy.chat),
                await msg_link(copy),
                get_display_name(sndr),
                inline_mention(sndr, custom=sndr.id),
                self.file,
            )
            try:
                if not copy.sticker:
                    await asyncio.sleep(5)
                    await upl.edit_caption(text)
            except Exception:
                LOGS.exception("Editing Dump Media. <(ignore)>")

    # Uploader functions

    async def video_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "video": self.file,
            "caption": self.pre_caption,
            "thumb": self.thumb,
            "duration": self.metadata["duration"],
            "height": self.metadata["height"],
            "width": self.metadata["width"],
            "disable_notification": self.silent,
        }
        type = "Video"
        self._log_info(type)
        args = self._progress_args(args)
        try:
            return await self.client.send_video(**args)
        except Exception as exc:
            self._handle_upload_error(type, exc)

    async def audio_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "audio": self.file,
            "caption": self.pre_caption,
            "thumb": self.thumb,
            "duration": self.metadata["duration"],
            "title": self.metadata["title"],
            "performer": self.metadata["artist"],
            "disable_notification": self.silent,
        }
        type = "Audio"
        self._log_info(type)
        args = self._progress_args(args)
        try:
            return await self.client.send_audio(**args)
        except Exception as exc:
            self._handle_upload_error(type, exc)

    async def animation_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "animation": self.file,
            "caption": self.pre_caption,
            "thumb": self.thumb,
            "height": self.metadata["height"],
            "width": self.metadata["width"],
            "disable_notification": self.silent,
        }
        type = "Animation"
        self._log_info(type)
        try:
            return await self.client.send_animation(**args)
        except Exception as exc:
            self._handle_upload_error(type, exc)

    async def document_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "document": self.file,
            "caption": self.pre_caption,
            "thumb": self.thumb,
            "disable_notification": self.silent,
        }
        type = "Document"
        self._log_info(type)
        args = self._progress_args(args)
        try:
            return await self.client.send_document(**args)
        except Exception as exc:
            self._handle_upload_error(type, exc)

    async def image_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "photo": self.file,
            "caption": self.pre_caption,
            "disable_notification": self.silent,
        }
        try:
            return await self.client.send_photo(**args)
        except Exception as exc:
            self._handle_upload_error("Image", exc)

    async def sticker_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "sticker": self.file,
            "disable_notification": self.silent,
        }
        try:
            return await self.client.send_sticker(**args)
        except Exception as exc:
            self._handle_upload_error("Sticker", exc)

    # Uploader helper functions.

    def _log_info(self, format):
        if self._log:
            n = LOGGER_MSG.format(format, self.file, self.dc, self.metadata["size"])
            LOGS.debug(n)

    def _progress_args(self, args):
        if self.show_progress and self.event:
            progress_args = (
                self.event,
                self.progress_text,
                time(),
                self.client,
                self.delay,
                self._cancelled,
            )
            args.update(
                {
                    "progress": self.progress,
                    "progress_args": progress_args,
                }
            )
        return args

    def _handle_upload_error(self, type, error):
        LOGS.exception(f"{type} Uploader: {self.file}")
        raise UploadError(
            f"{error.__class__.__name__} while uploading {type}: `{', '.join(error.args)}`",
        )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def videoThumb(_path, duration):
    default = path.join(getcwd(), "resources/extras/ultroid.jpg")
    if duration is False:
        dur = 1
    else:
        if duration > 1:
            dur = int(
                duration * choice((0.25, 0.33, 0.4, 0.45, 0.5, 0.55, 0.6, 0.66, 0.75))
            )
        else:
            dur = 1
    thumb_path = path.join(getcwd(), f"resources/temp/{random_string(8)}-{dur}.jpg")
    await bash(f"ffmpeg -ss {dur} -i {shq(_path)} -vframes 1 {shq(thumb_path)} -y")
    return thumb_path if path.exists(thumb_path) else default


async def audioThumb(_path):
    thumby = f"resources/temp/{random_string(8).lower()}.jpg"
    try:
        if not (album_art := load_file(_path).get("artwork")):
            return LOGS.error(f"no artwork found: {_path}")
        data = album_art.value.data
        thumb = Image.open(BytesIO(data))
        thumb.save(thumby)
        return thumby if path.exists(thumby) else None
    except BaseException as exc:
        return LOGS.error(exc)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class UploadError(Exception):
    pass


class ProcessCancelled(Exception):
    pass


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
