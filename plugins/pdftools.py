# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}pdf <page num> <reply to pdf file>`
    Extract & send page as an Image. (note-: For extracting all pages, just use .pdf)
    to upload selected range `{i}pdf 1-7`

• `{i}pdtext <page num> <reply to pdf file>`
    Extract Text From the Pdf.(note-: For Extraction all text just use .pdtext)
    to extract selected pages `{i}pdf 1-7`

• `{i}pdscan <reply to image>`
    It scan, crop & send image(s) as pdf.

• `{i}pdsave <reply to image/pdf>`
    It scan, crop & save file to merge.
    you can merge many pages in a single pdf.

• `{i}pdsend `
    Merge & send the pdf, collected from .pdsave.
"""

import asyncio
import glob
import time
from pathlib import Path
from shlex import quote

import cv2
import numpy as np
from telethon.errors import PhotoSaveFileInvalidError, ImageProcessFailedError

from pyUltroid.fns.tools import four_point_transform
from . import (
    HNDLR,
    LOGS,
    ULTConfig,
    bash,
    check_filename,
    get_string,
    mediainfo,
    osremove,
    tg_downloader,
    ultroid_cmd,
)

try:
    from pypdf import PdfMerger, PdfReader, PdfWriter
except ImportError:
    from PyPDF2 import PdfMerger, PdfReader, PdfWriter

try:
    from PIL import Image
except ImportError:
    Image = None
    LOGS.info(f"{__file__}: PIL  not Installed.")


@ultroid_cmd(
    pattern="pdf( (.*)|$)",
)
async def pdfseimg(event):
    ok = await event.get_reply_message()
    if not (
        ok and ok.media and ok.document and ok.document.mime_type == "application/pdf"
    ):
        return await event.eor("`Reply to PDF you want to extract as Image..`")

    xx = await event.eor(get_string("com_1"))
    msg = event.pattern_match.group(2)
    path, _ = await tg_downloader(media=ok, event=xx, show_progress=True)
    await xx.edit(f"`Extracting Image from {Path(path).name}..`")
    pdf = PdfReader(path)

    if not msg or "-" in msg:
        if msg and "-" in msg:
            r1, r2 = map(lambda i: int(i.strip()), msg.split("-", 1))
            _range = range(r1 - 1, r2)
        else:
            _range = range(len(pdf.pages))

        for num in _range:
            try:
                pw = PdfWriter()
                pw.add_page(pdf.pages[num])
                file = check_filename(f"pdf_extract_{num + 1}.png")
                with open(file, "wb") as f:
                    pw.write(f)
                pw.close()
                await xx.respond(f"`Page {num + 1}`", file=file)
            except (PhotoSaveFileInvalidError, ImageProcessFailedError):
                _file = check_filename(Path(file).with_suffix(".pdf"))
                Path(file).rename(_file)
                await xx.respond(f"`Page {num + 1}`", file=_file)
            except Exception:
                LOGS.exception("Error in Extracting PDF.!")
            finally:
                osremove(file)
                await asyncio.sleep(5)

    else:
        o = int(msg) - 1
        pw = PdfWriter()
        pw.add_page(pdf.pages[o])
        out = check_filename("pdf_extract.png")
        with open(out, "wb") as f:
            pw.write(f)
        pw.close()
        try:
            await xx.respond(f"`Successfully extracted Page {o}.`", file=out)
        except (PhotoSaveFileInvalidError, ImageProcessFailedError):
            _out = check_filename(Path(out).with_suffix(".pdf"))
            Path(out).rename(_out)
            await xx.respond(f"`Page {num + 1}`", file=_out)
        except Exception:
            LOGS.exception("Error in Extracting PDF.!!!")
        finally:
            osremove(out)

    osremove(path)
    await xx.delete()


@ultroid_cmd(
    pattern="pdtext( (.*)|$)",
)
async def pdfsetxt(event):
    ok = await event.get_reply_message()
    msg = event.pattern_match.group(2)
    if not (
        ok and ok.media and ok.document and ok.document.mime_type == "application/pdf"
    ):
        return await event.eor("`Reply the PDF you want to extract text from..`")

    xx = await event.eor(get_string("com_1"))
    path, _ = await tg_downloader(media=ok, event=xx, show_progress=True)
    await xx.edit(f"`Extracting text from PDF...`")
    if not msg:
        pdf = PdfReader(path)
        text = check_filename(Path(path).stem + "_extracted.txt")
        with open(text, "w") as f:
            for page_num in range(len(pdf.pages)):
                pageObj = pdf.pages[page_num]
                txt = pageObj.extract_text()
                f.write(f">>> Page {page_num + 1}\n")
                f.write("".center(100, "-"))
                f.write("\n\n" + txt + "\n\n")
        await ok.reply(
            "`Succesfully Extracted text from the PDF!`",
            file=text,
            thumb=ULTConfig.thumb,
        )
        osremove(text, path)
        await xx.delete()
        return

    if "-" in msg:
        u, d = msg.split("-")
        a = PdfReader(path)
        content = "".join(a.pages[i].extract_text() for i in range(int(u) - 1, int(d)))
        text = check_filename(Path(path).stem + f"_extracted_{msg}.txt")
    else:
        u = int(msg) - 1
        a = PdfReader(path)
        content = a.pages[u].extract_text()
        text = check_filename(Path(path).stem + f"_extracted_{msg}.txt")

    with open(text, "w") as f:
        f.write(content)
    await ok.reply(
        "`Succesfully Extracted text from the PDF!`", file=text, thumb=ULTConfig.thumb
    )
    osremove(text, path)
    await xx.delete()


@ultroid_cmd(
    pattern="pdscan( (.*)|$)",
)
async def imgscan(event):
    ok = await event.get_reply_message()
    if not ((ok and ok.media) and "pic" in mediainfo(ok.media)):
        return await event.eor("`Reply to Media u Want to Scan as PDF..`")

    xx = await event.eor(get_string("com_1"))
    ultt, _ = await tg_downloader(media=ok, event=xx, show_progress=False)
    image = cv2.imread(ultt)
    original_image = image.copy()
    ratio = image.shape[0] / 500.0
    hi, wid = image.shape[:2]
    ra = 500 / float(hi)
    dmes = (int(wid * ra), 500)
    image = cv2.resize(image, dmes, interpolation=cv2.INTER_AREA)
    image_yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
    image_y = np.zeros(image_yuv.shape[:2], np.uint8)
    image_y[:, :] = image_yuv[:, :, 0]
    image_blurred = cv2.GaussianBlur(image_y, (3, 3), 0)
    edges = cv2.Canny(image_blurred, 50, 200, apertureSize=3)
    contours, hierarchy = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    polygons = []
    for cnt in contours:
        hull = cv2.convexHull(cnt)
        polygons.append(cv2.approxPolyDP(hull, 0.01 * cv2.arcLength(hull, True), False))
        sortedPoly = sorted(polygons, key=cv2.contourArea, reverse=True)
        cv2.drawContours(image, sortedPoly[0], -1, (0, 0, 255), 5)
        simplified_cnt = sortedPoly[0]
    if len(simplified_cnt) == 4:
        try:
            from skimage.filters import threshold_local
        except ImportError:
            LOGS.info(f"Scikit-Image is not Installed.")
            await xx.edit("`Installing Scikit-Image, This may take some time...`")
            await bash("pip install -q scikit-image")
            from skimage.filters import threshold_local

        cropped_image = four_point_transform(
            original_image,
            simplified_cnt.reshape(4, 2) * ratio,
        )
        gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
        T = threshold_local(gray_image, 11, offset=10, method="gaussian")
        ok = (gray_image > T).astype("uint8") * 255
    else:
        ok = cv2.detailEnhance(original_image, sigma_s=10, sigma_r=0.15)

    Path("pdf").mkdir(exist_ok=True)
    out = check_filename("scanned.png")
    cv2.imwrite(out, ok)
    image1 = Image.open(out)
    im1 = image1.convert("RGB")
    scann = check_filename("pdf/scanned.pdf")
    im1.save(scann)
    await ok.reply("`Scanned Successfully!`", file=scann, thumb=ULTConfig.thumb)
    osremove(ultt, out, scann)
    await xx.delete()


@ultroid_cmd(
    pattern="pdsave( (.*)|$)",
)
async def savepdf(event):
    ok = await event.get_reply_message()
    if not (ok and ok.media):
        return await event.eor(
            "`Reply to Images/pdf which u want to merge as single pdf..`",
        )

    xx = await event.eor(get_string("com_1"))
    Path("pdf").mkdir(exist_ok=True)
    ultt, _ = await tg_downloader(media=ok, event=xx, show_progress=False)
    if ultt.endswith(("png", "jpg", "jpeg", "webp")):
        image = cv2.imread(ultt)
        original_image = image.copy()
        ratio = image.shape[0] / 500.0
        h_, _v = image.shape[:2]
        m_ = 500 / float(h_)
        image = cv2.resize(image, (int(_v * m_), 500), interpolation=cv2.INTER_AREA)
        image_yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
        image_y = np.zeros(image_yuv.shape[:2], np.uint8)
        image_y[:, :] = image_yuv[:, :, 0]
        image_blurred = cv2.GaussianBlur(image_y, (3, 3), 0)
        edges = cv2.Canny(image_blurred, 50, 200, apertureSize=3)
        contours, hierarchy = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        polygons = []
        for cnt in contours:
            hull = cv2.convexHull(cnt)
            polygons.append(
                cv2.approxPolyDP(hull, 0.01 * cv2.arcLength(hull, True), False),
            )
            sortedPoly = sorted(polygons, key=cv2.contourArea, reverse=True)
            cv2.drawContours(image, sortedPoly[0], -1, (0, 0, 255), 5)
            simplified_cnt = sortedPoly[0]
        if len(simplified_cnt) == 4:
            try:
                from skimage.filters import threshold_local

            except ImportError:
                LOGS.info(f"Scikit-Image is not Installed.")
                await xx.edit(
                    "`Installing Scikit-Image...\nThis may take some time...`"
                )
                await bash("pip install -q scikit-image")
                from skimage.filters import threshold_local

            cropped_image = four_point_transform(
                original_image,
                simplified_cnt.reshape(4, 2) * ratio,
            )
            gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
            T = threshold_local(gray_image, 11, offset=10, method="gaussian")
            ok = (gray_image > T).astype("uint8") * 255
        if len(simplified_cnt) != 4:
            ok = cv2.detailEnhance(original_image, sigma_s=10, sigma_r=0.15)

        out = check_filename("_merge.png")
        cv2.imwrite(out, ok)
        image1 = Image.open(out)
        im1 = image1.convert("RGB")
        a = check_filename("pdf/scan_merged.pdf")
        im1.save(a)
        osremove(out)
        await xx.edit(
            f"__Done, Now reply to another Image or PDF to merge.__\n\n`If Completed then use {HNDLR}pdsend to Merge and send as PDF.`",
        )
    elif ultt.endswith(".pdf"):
        a = check_filename("pdf/scan_merged.pdf")
        await bash(f"mv -f {quote(ultt)} {quote(a)}")
        await xx.edit(
            f"__Done, Now reply to another Image or PDF to merge.__\n\n`If Completed then use {HNDLR}pdsend to Merge and send as PDF.`",
        )
    else:
        await xx.edit("`Reply to a Image/pdf only...`")
    osremove(ultt)


@ultroid_cmd(
    pattern="pdsend( (.*)|$)",
)
async def sendpdf(event):
    afl = glob.glob("pdf/*_merged*pdf")
    if not afl:
        return await event.eor(
            "first select pages by replying .pdsave of which u want to make multi page pdf file",
        )

    xx = await event.eor(get_string("com_1"))
    msg = event.pattern_match.group(2) or "Merged PDF file.pdf"
    ok = msg if msg.lower().endswith(".pdf") else f"{msg}.pdf"
    merger = PdfMerger()
    for item in sorted(afl):
        merger.append(item)
    merger.write(ok)
    merger.close()
    await xx.respond(
        f"`Merged {len(afl)} files into single PDF file.`",
        file=ok,
        thumb=ULTConfig.thumb,
    )
    osremove(ok, "pdf", folders=True)
    await xx.delete()
