# PyroGram Download and Upload.
# Written by (@ah3h3,  @spemgod) for fast upload and downloads.
#
# Edited on 21-07-2022:
#  - created class pyroUL
#  - changed lots of helper functions.
#  - added pyroDL on 23-07
#

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
from telethon.errors.rpcerrorlist import MessageNotModifiedError

from pyrog import app
from .helper import bash, time_formatter, inline_mention, cleargif, msg_link
from .tools import media_info, check_filename, humanbytes, shq
from .. import LOGS, udB, ultroid_bot, asst


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DUMP_CHANNEL = udB.get_key("TAG_LOG")
PROGRESS_LOG = {}

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
    if is_cancelled:
        client.stop_transmission()
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
    except MessageNotModifiedError:
        LOGS.exception("pyro progress err: ")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class pyroDL:
    def __init__(self, event, source, show_progress=True):
        self._cancelled = False
        self.event = event
        self.source = source
        self.show_progress = show_progress
        self.dc = 1

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
            msg = await self.source.copy(
                DUMP_CHANNEL,
                caption="#pyroDL \n\n" + self.source.text,
            )
            if _msg := getattr(msg, "document", None):
                self.dc = _msg.dc_id
            return msg
        except BaseException as exc:
            LOGS.exception("pyroDL: err copying file: ")
            return f"Error copying file: `{exc}`"

    async def download(self, **kwargs):
        _msg = await self.copy_msg()
        if type(_msg) is str:
            return await self.event.edit(_msg)
        await asyncio.sleep(0.6)
        self.msg = await self.client.get_messages(DUMP_CHANNEL, _msg.id)
        self.updateAttrs(kwargs)
        self.client = app(self.dc)
        dl = await self.dls()
        if self.auto_edit:
            if isinstance(dl, Exception):
                await self.event.edit(f"err in pyroDL: `{dl}`")
            else:
                await self.event.edit(
                    f"Downloaded \n`{self.filename}` \nin {self.dl_time}"
                )

    async def dls(self):
        args = {"message": self.msg, "file_name": self.filename}
        if self._log:
            LOGS.debug(f"Downloading | [DC {self.dc}] | {self.filename}")
        if self.show_progress:
            prog_args = (self.event, self.progress_text, time(), self.client, self.delay, self._cancelled)
            args.update({"progress": self.progress, "progress_args": prog_args})
        try:
            stime = time()
            dlx = await self.client.download_media(**args)
        except BaseException as exc:
            LOGS.exception("PyroDL err: ")
            return exc
        else:
            self.dl_time = time_formatter((time() - stime) * 1000)
            return dlx
        finally:
            if self.schd_delete:
                asst.loop.create_task(self.delTask(self.msg))

    async def delTask(self, task):
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
        self._cancelled = False
        self.path = self.listFiles(_path)
        self.show_progress = show_progress

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
            return tuple(col) if col else f"Folder is Empty: `{_path}`"
        else:
            return f"Wrong Path: `{_path}`"

    def defaultValues(self):
        self.chat_id = DUMP_CHANNEL
        self.delete_file = False
        self.delete_thumb = True
        self.schd_delete = False
        self.auto_edit = True
        self.return_obj = False  # only for single file
        self.dc = 1
        self._log = True
        self.success = 0
        self.failed = 0
        self.silent = True
        self.force_document = False
        self.delay = 8  # progress_delay
        self.thumb = None

    def updateAttrs(self, kwargs, file, count):
        self.file = file
        self.count = count
        event = getattr(self, "event", None)
        self.reply_to = (event.reply_to_msg_id or event.id) if event else None
        self.copy_to = event.chat_id if event else DUMP_CHANNEL
        if self.show_progress:
            self.progress = pyro_progress
            self.progress_text = (
                f"`{self.count}/{len(self.path)} | Uploading {self.file}..`"
            )
        if list(filter(bool, [kwargs.pop(i, None) for i in ("schd_delete", "df")])):
            self.schd_delete = True
        for k, v in kwargs.items():
            setattr(self, k, v)

    async def upload(self, **kwargs):
        if type(self.path) is str:
            return await self.event.edit(self.path)
        self.defaultValues()
        self.pre_time = time()
        for count, file in enumerate(sorted(self.path), start=1):
            self.updateAttrs(kwargs, file, count)
            self.client = app(self.dc)
            if sizerr := self.checkSize(self.file):
                await self.event.edit(sizerr)
                await asyncio.sleep(self.sleepTime())
                continue
            _ulfunc = await self.getMetadata()
            out = await _ulfunc()
            await self.cleanup()  # caption
            if self.return_obj:
                return out
            if err := await self.finalize(out):
                await self.event.edit("`Error While Copying file...`")
                await asyncio.sleep(self.sleepTime())
                continue
            await self.handleEdits(out=out, finished=False)
            await asyncio.sleep(self.sleepTime())
        await self.handleEdits(finished=True)

    @staticmethod
    def checkSize(_path):
        size = path.getsize(_path)
        if size > 2097152000:
            return "`File Size is Greater than 2GB..`"
        elif size == 0:
            return "`File Size = 0 B...`"

    def sleepTime(self):
        return 3.5 if len(self.path) < 13 else 6

    async def getMetadata(self):
        self.metadata = media_info(self.file)
        self.pre_caption = getattr(self, "caption", None) if self.return_obj else None
        type = self.metadata.get("type").lower()
        if not (hasattr(self, "thumb") and self.force_document):
            if type == "video":
                self.thumb = await videoThumb(self.file, self.metadata["duration"])
            elif type == "audio":
                self.thumb = await audioThumb(self.file)
            elif type == "gif":
                self.thumb = await videoThumb(self.file, False)
        self.handleWebm(type)
        self.start_time = time()
        return self.get_type(type)

    def handleWebm(self, type):
        if type != "sticker" and self.file.lower().endswith(".webm"):
            ext = "" if self.file[:-5].lower().endswith(".mkv") else ".mp4"
            new_pth = check_filename(self.file[:-5] + ext)
            rename(self.file, new_pth)
            self.file = new_pth

    def get_type(self, type):
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

    async def cleanup(self):
        if not hasattr(self, "caption"):
            caption = "**Uploaded in {0}.** \n**-** `{1}` \n**-** ```{2}```"
            self.caption = caption.format(
                self.ul_time, self.metadata["size"], self.file
            )
        if self.delete_file:
            remove(self.file)
        if x := getattr(self, "thumb", None):
            if self.delete_thumb and "ultroid.jpg" not in x:
                remove(x)

    async def finalize(self, msg):
        try:
            await asyncio.sleep(1)
            file = await self.event.client.get_messages(msg.chat.id, ids=msg.id)
            if not (file and file.media):
                raise BaseException("Media not found // Error occurred in Uploading.")
            fx = await file.copy(
                self.copy_to,
                caption=self.caption,
                silent=self.silent,
                reply_to=self.reply_to,
            )
        except BaseException as exc:
            LOGS.exception("Err while copying file: ")
            return exc
        else:
            asst.loop.create_task(self.coroutineTask(msg, fx))
        finally:
            for attr in ("thumb", "caption"):
                if hasattr(self, attr):
                    delattr(self, attr)

    async def coroutineTask(self, m1, m2):
        if m2.gif and not m2.client._bot:
            await cleargif(m2)
        await asyncio.sleep(getattr(self, "cleanup_sleep", 2.5))
        if self.schd_delete:
             await m1.delete()
        else:
            dumpCaption = "#PyroUL ~ {0} \n–  [{1}]({2}) \n–  {3}: {4} \n–  `{5}`"
            sndr = m2.sender or await m2.get_sender()
            text = dumpCaption.format(
                f"{self.count}/{len(self.path)}",
                get_display_name(m2.chat),
                await msg_link(m2),
                get_display_name(sndr),
                inline_mention(sndr, custom=sndr.id),
                self.file,
            )
            try:
                if not m2.sticker:
                    await m1.edit_caption(text)
            except BaseException:
                LOGS.exception("editing dump media (pass):")

    async def handleEdits(self, out=None, finished=False):
        if finished:
            if len(self.path) > 1 and self.auto_edit:
                txt = f"`Uploaded {self.success} files in {time_formatter((time() - self.pre_time) * 1000)}`"
                if self.failed > 0:
                    txt += f"\n\n`Got #Error in {self.failed} files.`"
                await self.event.edit(txt)
            return
        if isinstance(out, BaseException):
            txt = f"__Error While Uploading:__ \n~ `{self.file}`\n\n~ `{out}`"
            self.failed += 1
        else:
            txt = f"__Successfully Uploaded:__  `{self.file}`"
            self.success += 1
        if self.auto_edit:
            await self.event.edit(txt)

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
        if self._log:
            LOGS.debug(
                f"Uploading Video | Path: {self.file} | DC: {self.dc} | Size: {self.metadata['size']}"
            )
        if self.show_progress:
            prog_args = (self.event, self.progress_text, time(), self.client, self.delay, self._cancelled)
            args.update({"progress": self.progress, "progress_args": prog_args})
        try:
            vid = await self.client.send_video(**args)
            self.ul_time = time_formatter((time() - self.start_time) * 1000)
            return vid
        except BaseException as exc:
            LOGS.exception(f"Video Uploader: {self.file}")
            return exc

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
        if self._log:
            LOGS.debug(
                f"Uploading Audio | Path: {self.file} | DC: {self.dc} | Size: {self.metadata['size']}"
            )
        if self.show_progress:
            prog_args = (self.event, self.progress_text, time(), self.client, self.delay, self._cancelled)
            args.update({"progress": self.progress, "progress_args": prog_args})
        try:
            song = await self.client.send_audio(**args)
            self.ul_time = time_formatter((time() - self.start_time) * 1000)
            return song
        except BaseException as exc:
            LOGS.exception(f"Audio Uploader: {self.file}")
            return exc

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
        try:
            img = await self.client.send_animation(**args)
            self.ul_time = time_formatter((time() - self.start_time) * 1000)
            return img
        except BaseException as exc:
            LOGS.exception(f"Animation Uploader: {self.file}")
            return exc

    async def document_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "document": self.file,
            "caption": self.pre_caption,
            "thumb": self.thumb,
            "disable_notification": self.silent,
        }
        if self._log:
            LOGS.debug(
                f"Uploading Document | Path: {self.file} | DC: {self.dc} | Size: {self.metadata['size']}"
            )
        if self.show_progress:
            prog_args = (self.event, self.progress_text, time(), self.client, self.delay, self._cancelled)
            args.update({"progress": self.progress, "progress_args": prog_args})
        try:
            doc = await self.client.send_document(**args)
            self.ul_time = time_formatter((time() - self.start_time) * 1000)
            return doc
        except BaseException as exc:
            LOGS.exception(f"Document Uploader: {self.file}")
            return exc

    async def image_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "photo": self.file,
            "caption": self.pre_caption,
            "disable_notification": self.silent,
        }
        try:
            img = await self.client.send_photo(**args)
            self.ul_time = time_formatter((time() - self.start_time) * 1000)
            return img
        except BaseException as exc:
            LOGS.exception(f"Image Uploader: {self.file}")
            return exc

    async def sticker_uploader(self):
        args = {
            "chat_id": self.chat_id,
            "sticker": self.file,
            "disable_notification": self.silent,
        }
        try:
            stic = await self.client.send_sticker(**args)
            self.ul_time = time_formatter((time() - self.start_time) * 1000)
            return stic
        except BaseException as exc:
            LOGS.exception(f"Sticker Uploader: {self.file}")
            return exc


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
