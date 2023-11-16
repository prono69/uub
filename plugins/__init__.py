# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

import asyncio
import os
import re
import time
from random import choice

import requests
from telethon import Button, events
from telethon.tl import functions, types  # pylint:ignore

from pyUltroid import *
from pyUltroid._misc._assistant import asst_cmd, callback, in_pattern
from pyUltroid._misc._decorators import ultroid_cmd
from pyUltroid._misc._wrappers import eod, eor
from pyUltroid.dB import DEVLIST, ULTROID_IMAGES
from pyUltroid.fns.helper import *
from pyUltroid.fns.misc import *
from pyUltroid.fns.tools import *

# from pyUltroid.startup._database import _BaseDatabase
from pyUltroid.version import __version__, ultroid_version
from strings import get_help, get_string

# custom
from pyUltroid.custom.commons import *
from pyUltroid.custom.functions import *
from pyUltroid.custom.mediainfo import gen_mediainfo


quotly = Quotly()
Telegraph = telegraph_client()

Redis = udB.get_key
con = TgConverter

# udB: _BaseDatabase
# asst: UltroidClient
# ultroid_bot: UltroidClient

OWNER_NAME = ultroid_bot.full_name
OWNER_ID = ultroid_bot.uid

LOG_CHANNEL = udB.get_key("LOG_CHANNEL")
TAG_LOG = udB.get_key("TAG_LOG")

# used in plugins, don't touch
InlinePlugin = {}
STUFF = {}


def inline_pic():
    INLINE_PIC = udB.get_key("INLINE_PIC")
    if INLINE_PIC is None:
        INLINE_PIC = choice(ULTROID_IMAGES)
    elif INLINE_PIC == False:
        INLINE_PIC = None
    return INLINE_PIC


# extra stuff
List = []
Dict = {}
N = 0
h1, h2 = [], {}
h3, h4 = set(), 0

# Chats, which needs to be ignore for some cases
# Considerably, there can be many
# Feel Free to Add Any other...
NOSPAM_CHAT = [
    -1001361294038,  # UltroidSupportChat
    -1001387666944,  # PyrogramChat
    -1001109500936,  # TelethonChat
    -1001050982793,  # Python
    -1001256902287,  # DurovsChat
    -1001473548283,  # SharingUserbot
]

ATRA_COL = (
    "DarkCyan",
    "DeepSkyBlue",
    "DarkTurquoise",
    "Cyan",
    "LightSkyBlue",
    "Turquoise",
    "MediumVioletRed",
    "Aquamarine",
    "Lightcyan",
    "Azure",
    "Moccasin",
    "PowderBlue",
)


async def _get_colors(pick=True):
    path = "resources/colorlist.txt"
    if os.path.exists(path):
        data = await asyncread(path)
        data = data.splitlines()
        return choice(data) if pick else data
    return "RoyalBlue" if pick else ["RoyalBlue"]
