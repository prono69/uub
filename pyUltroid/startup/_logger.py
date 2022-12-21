import logging
from os import environ, getenv, path, remove
from platform import python_version, python_version_tuple

from telethon import __version__
from telethon.tl.alltlobjects import LAYER

from ._extra import _fix_logging, _ask_input
from ..fns.tglogger import TGLogHandler
from .. import ultroid_version, __version__ as __pyUltroid__


# ----------------------------------------------------------------------------


def where_hosted():
    if getenv("DYNO"):
        return "heroku"
    if getenv("RAILWAY_STATIC_URL"):
        return "railway"
    if getenv("OKTETO_TOKEN"):
        return "okteto"
    if getenv("KUBERNETES_PORT"):
        return "qovery | kubernetes"
    if getenv("RUNNER_USER") or getenv("HOSTNAME"):
        return "github actions"
    if getenv("ANDROID_ROOT"):
        return "termux"
    if getenv("FLY_APP_NAME"):
        return "fly.io"
    return "local"


# ----------------------------------------------------------------------------

LOGS = logging.getLogger("pyUltLogs")
LOGS.setLevel(logging.DEBUG)
TelethonLogger = logging.getLogger("Telethon")

# ----------------------------------------------------------------------------

HOSTED_ON = where_hosted()
LOG_HANDLERS = []
log_file = "ultroid.log"

# ----------------------------------------------------------------------------

if int(python_version_tuple()[1]) < 10:
    _fix_logging(logging.FileHandler)
if HOSTED_ON == "local" or getenv("HOST") == "local":
    _ask_input()

# ----------------------------------------------------------------------------

if path.isfile(log_file):
    remove(log_file)
if data := getenv("LOGGER_DATA"):
    LOG_DATA = eval(data)
    environ.pop("LOGGER_DATA", 0)
else:
    LOG_DATA = {}

# ----------------------------------------------------------------------------

log_level = logging.INFO if LOG_DATA.get("verbose") is True else logging.WARNING
TelethonLogger.setLevel(log_level)

for i in ("pyrogram", "apscheduler"):
    logging.getLogger(i).setLevel(logging.WARNING)
for i in ("pyrogram.parser.html", "pyrogram.session.session"):
    logging.getLogger(i).setLevel(logging.ERROR)

# ----------------------------------------------------------------------------

og_format = "%(asctime)s | %(name)s [%(levelname)s] : %(message)s"
log_format1 = logging.Formatter(og_format, datefmt="%m/%d/%Y, %H:%M:%S")

_logger_name = LOG_DATA.get("name", "TGLogger")
log_format2 = logging.Formatter(
    f"{_logger_name} [%(levelname)s] ~ %(asctime)s\n» Line %(lineno)s: %(filename)s\n» %(message)s",
    datefmt="%H:%M:%S",
)

# ----------------------------------------------------------------------------

file_handler = logging.FileHandler(log_file)
stream_handler = logging.StreamHandler()
for hndlr in (file_handler, stream_handler):
    hndlr.setLevel(logging.INFO)
    hndlr.setFormatter(log_format1)
LOG_HANDLERS.extend([file_handler, stream_handler])

# ----------------------------------------------------------------------------

if LOG_DATA.get("tglog") is True:
    tglogger = TGLogHandler(
        chat=LOG_DATA.get("chat"),
        token=LOG_DATA.get("token"),
    )
    tglogger.setLevel(logging.DEBUG)
    tglogger.setFormatter(log_format2)
    LOG_HANDLERS.append(tglogger)

# ----------------------------------------------------------------------------

# Initiate all Loggers!
logging.basicConfig(handlers=LOG_HANDLERS)
del LOG_DATA, LOG_HANDLERS

# ----------------------------------------------------------------------------

if getenv("HOST") == "local":
    try:
        import coloredlogs

        coloredlogs.install(level=None, logger=LOGS, fmt=og_format)
    except ImportError:
        pass

# ----------------------------------------------------------------------------

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
