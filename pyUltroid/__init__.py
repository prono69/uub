# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import os
import sys

from ._helpers import on_startup, post_startup
from .version import __version__, ultroid_version

run_as_module = True
start_time, Var = on_startup()


class ULTConfig:
    lang = "en"
    thumb = "resources/extras/ultroid.jpg"


from .startup import *
from .startup._database import UltroidDB
from .startup.BaseClient import UltroidClient
from .startup.connections import validate_session, vc_connection
from .startup.funcs import autobot, enable_inline


if not os.path.exists("./plugins"):
    LOGS.error("'plugins' folder not found!\nMake sure that, you are on correct path.")
    exit()

_ult_cache = {}
_ignore_eval = []
udB = UltroidDB()

# LOGS.info(f"Connecting to {udB.name} ...")
if udB.ping():
    LOGS.info(f"Connected to {udB.name} Successfully!")

BOT_MODE = udB.get_key("BOTMODE")
DUAL_MODE = udB.get_key("DUAL_MODE")

if BOT_MODE:
    if DUAL_MODE:
        udB.del_key("DUAL_MODE")
        DUAL_MODE = False
    ultroid_bot = None

    if not udB.get_key("BOT_TOKEN"):
        LOGS.critical('"BOT_TOKEN" not Found! Please add it, in order to use "BOTMODE"')
        sys.exit()
else:
    ultroid_bot = UltroidClient(
        validate_session(Var.SESSION, LOGS),
        udB=udB,
        app_version=ultroid_version,
        device_model="Ultroid",
        proxy=udB.get_key("TG_PROXY"),
    )
    ultroid_bot.run_in_loop(autobot())

asst = UltroidClient(None, bot_token=udB.get_key("BOT_TOKEN"), udB=udB)

if BOT_MODE:
    ultroid_bot = asst
    if udB.get_key("OWNER_ID"):
        try:
            ultroid_bot.me = ultroid_bot.run_in_loop(
                ultroid_bot.get_entity(udB.get_key("OWNER_ID"))
            )
        except Exception as er:
            LOGS.exception(er)
elif not asst.me.bot_inline_placeholder:
    ultroid_bot.run_in_loop(enable_inline(ultroid_bot, asst.me.username))

vcClient = vc_connection(udB, ultroid_bot)

HNDLR = udB.get_key("HNDLR") or "."
DUAL_HNDLR = udB.get_key("DUAL_HNDLR") or "/"
SUDO_HNDLR = udB.get_key("SUDO_HNDLR") or HNDLR

# multidb, web-service, version_change, updatenv
post_startup()

try:
    del (
        on_startup,
        enable_inline,
        post_startup,
        UltroidDB,
        vc_connection,
        validate_session,
        autobot,
        UltroidClient,
    )
except:
    pass
