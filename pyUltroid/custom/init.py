__all__ = []

import asyncio
from os import environ, system
from pathlib import Path
from subprocess import run, Popen
from time import tzset

from ._loop import loop, run_async_task, tasks_db

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


def startup_logo():
    # skipping bash startup
    print(
        """
            ┏┳┓╋┏┓╋╋╋╋┏┓┏┓
            ┃┃┣┓┃┗┳┳┳━╋╋┛┃
            ┃┃┃┗┫┏┫┏┫╋┃┃╋┃
            ┗━┻━┻━┻┛┗━┻┻━┛

      Visit @TheUltroid for updates!!

"""
    )


def cleanup_stuff():
    hitlist = [
        "/usr/local/lib/python3.*/site-packages/pip/_vendor/.wh*",
        "/usr/local/lib/python3.*/site-packages/.wh.pip*",
        "/usr/local/lib/python3.*/site-packages/.wh.setuptools*",
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
    if not Path("plugins").is_dir():
        print("Plugins Folder does not exists!")
        quit(0)
    startup_logo()
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


async def _updater_task(data):
    try:
        from redis.asyncio import Redis
    except ImportError as e:
        return LOGS.critical(e)

    key, password, other = data.split(" ", maxsplit=2)
    host, port = other.split(":", maxsplit=1)
    while True:
        r = Redis(
            host=host,
            password=password,
            port=port,
            decode_responses=True,
            socket_timeout=10,
        )
        await r.setex(key, 1200, 1205)
        del r
        await asyncio.sleep(1200)


def _host_specifics():
    if Var.HOST.lower() == "heroku":
        LOGS.debug("Setting up heroku3 API")
        herokuApp()
    if r_data := environ.get("USR_STATUS_UPDATE"):  # chk doprax?
        run_async_task(_updater_task, r_data, id="status_update")
    if environ.get("qBit") and Path("1337x").is_file():
        LOGS.info("Starting qBittorrent")
        Popen("bash 1337x &", shell=True)


def delayed_startup_tasks():
    undel = ("local", "railway", "wfs", "doprax")
    env = Path(".env")
    if Var.HOST.lower() not in undel and env.is_file():
        env.unlink()
    _host_specifics()


# doprax checks
def afterBoot(db):
    if Var.HOST.lower() == "doprax":
        chk = environ.get("CHECKS")
        if not chk or (chk and chk not in db.get_key("DOPRAX")):
            print("check the 'CHECKS' Var...")
            quit(0)


delayed_startup_tasks()
