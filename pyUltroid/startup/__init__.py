# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import os
import sys
import logging

from .. import ultroid_version, Var, __version__ as __pyUltroid__


def where_hosted():
    if os.getenv("DYNO"):
        return "heroku"
    if os.getenv("RAILWAY_STATIC_URL"):
        return "railway"
    if os.getenv("OKTETO_TOKEN"):
        return "okteto"
    if os.getenv("KUBERNETES_PORT"):
        return "qovery | kubernetes"
    if os.getenv("RUNNER_USER") or os.getenv("HOSTNAME"):
        return "github actions"
    if os.getenv("ANDROID_ROOT"):
        return "termux"
    if os.getenv("FLY_APP_NAME"):
        return "fly.io"
    return "local"


HOSTED_ON = where_hosted()
LOGS = logging.getLogger("pyUltLogs")
LOGS.setLevel(logging.DEBUG)
TelethonLogger = logging.getLogger("Telethon")


def startup_main(LOGS, TelethonLogger):
    from platform import python_version, python_version_tuple

    from telethon import __version__
    from telethon.tl.alltlobjects import LAYER
    from tglogging import TelegramLogHandler

    from ._extra import _fix_logging, _ask_input


    file = "ultroid.log"
    if os.path.exists(file):
        os.remove(file)

    if data := os.getenv("LOGGER_DATA"):
        LOG_DATA = eval(data)
        os.environ.pop("LOGGER_DATA")
    else:
        LOG_DATA = {}

    log_level = logging.INFO if LOG_DATA.get("verbose") is True else logging.WARNING
    TelethonLogger.setLevel(log_level)
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    for muts in ("pyrogram.parser.html", "pyrogram.session.session"):
        logging.getLogger(muts).setLevel(logging.ERROR)

    if int(python_version_tuple()[1]) < 10:
        _fix_logging(logging.FileHandler)

    if HOSTED_ON == "local":
        _ask_input()

    log_format1 = logging.Formatter(
        "%(asctime)s | %(name)s [%(levelname)s] : %(message)s",
        datefmt="%m/%d/%Y, %H:%M:%S",
    )
    _logger_name = LOG_DATA.get("name", "TGLogger")
    log_format2 = logging.Formatter(
        f"\n\n{_logger_name} [%(levelname)s] ~ %(asctime)s \n» Line %(lineno)s in %(filename)s \n» %(message)s",
        datefmt="%H:%M:%S",
    )

    LOG_HANDLERS = []

    file_handler = logging.FileHandler(file)
    stream_handler = logging.StreamHandler()
    for hndlr in (file_handler, stream_handler):
        hndlr.setLevel(logging.INFO)
        hndlr.setFormatter(log_format1)

    LOG_HANDLERS.extend([file_handler, stream_handler])

    if LOG_DATA.get("tglog") is True:
        data = {
            "token": LOG_DATA.get("token"),
            "log_chat_id": LOG_DATA.get("chat"),
            "update_interval": LOG_DATA.get("interval", 8),
            "minimum_lines": LOG_DATA.get("lines", 1),
            "pending_logs": LOG_DATA.get("pending", 20000),
        }
        tglog = TelegramLogHandler(**data)
        tglog.setLevel(logging.DEBUG)
        tglog.setFormatter(log_format2)
        LOG_HANDLERS.append(tglog)

    # Initiate all Loggers!
    logging.basicConfig(handlers=LOG_HANDLERS)

    LOGS.info(
        """
                    -----------------------------------
                            Starting Deployment
                    -----------------------------------
    """
    )

    LOGS.info(f"Python version - {python_version()}")
    LOGS.info(f"py-Ultroid Version - {__pyUltroid__}")
    LOGS.info(f"Telethon Version - {__version__} [Layer: {LAYER}]")
    LOGS.info(f"Ultroid Version - {ultroid_version} [{HOSTED_ON}]")


startup_main(LOGS, TelethonLogger)

try:
    from safety.tools import *

    del startup_main
except ImportError:
    LOGS.error("'safety' package not found!")
