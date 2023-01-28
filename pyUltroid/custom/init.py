__all__ = []

from os import environ, system
from pathlib import Path
from subprocess import run, Popen
from time import tzset

from ._loop import loop

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


def cleanup_stuff():
    hitlist = [
        "/usr/local/lib/python3.*/site-packages/pip/_vendor/.wh.appdirs.py",
        "/usr/local/lib/python3.*/site-packages/.wh.pip-*",
        "/usr/local/lib/python3.*/site-packages/.wh.setuptools-*",
    ]
    for path in hitlist:
        run(f"rm -rfv {path}", shell=True)
    to_del = ("jewel", "bird", ".wget-hsts", "prvenv")
    for path in map(lambda i: Path(i), to_del):
        if path.is_file():
            path.unlink()


def setup_timezone():
    # use db for this !?
    TZ = environ.get("TZ", "Asia/Kolkata")
    try:
        environ["TZ"] = TZ
    except Exception:
        environ["TZ"] = "UTC"
    finally:
        tzset()


def telethon_checker():
    # todo: various telethon checks..
    def _layer():
        from telethon.tl.alltlobjects import LAYER

        return LAYER

    if _layer() < 151:
        run(
            "pip3 uninstall telethon -y && pip3 install https://github.com/New-dev0/Telethon/archive/platy.zip",
            shell=True,
        )


def startup_tasks():
    cleanup_stuff()
    setup_timezone()
    if load_dotenv and Path(".env").is_file():
        load_dotenv(override=True)
    telethon_checker()


startup_tasks()


# startup part 2

from pyUltroid.configs import Var
from pyUltroid.startup import LOGS
from .heroku import herokuApp


def _host_specifics():
    if Var.HOST.lower() == "heroku":
        LOGS.debug("Setting up Heroku API")
        herokuApp()
    if environ.get("qBit") and Path("1337x").is_file():
        LOGS.info("Starting qBittorrent")
        Popen("bash 1337x &", shell=True)


def delayed_startup_tasks():
    env = Path(".env")
    if Var.HOST.lower() not in ("local", "railway", "wfs") and env.is_file():
        env.unlink()
    _host_specifics()


delayed_startup_tasks()
