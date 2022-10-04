# some custom helper functions

from asyncio import iscoroutinefunction as awaitable
from dotenv import load_dotenv
from functools import wraps
from os import environ, path, remove, system
from time import time, tzset, perf_counter


def osremove(*args, folders=False, verbose=False):
    from . import LOGS

    if not args:
        return
    for arg in args:
        if type(arg) in (list, tuple, set):
            osremove(*arg)
            continue
        elif path.isfile(arg):
            _func = remove
        elif path.isdir(arg):
            from shutil import rmtree

            if not folders:
                continue
            _func = rmtree
        else:
            if verbose:
                LOGS.error(f"osremove: Invalid path ~ {arg}")
            continue

        try:
            _func(arg)
        except BaseException:
            if verbose:
                LOGS.exception(f"err in osremove: {path = }")


# https://gist.github.com/DougAF/ef88f89d1d99763bb05afd81285ef233#file-timer-py
def timeit(func):
    """To Check running time of functions."""
    if awaitable(func):

        @wraps(func)
        async def exec_time(*args, **kwargs):
            start = perf_counter()
            result = await func(*args, **kwargs)
            time_taken = perf_counter() - start
            return f"Function: {func.__name__} \nTime taken: {time_taken:.4f} seconds."

        return exec_time
    else:

        @wraps(func)
        def exec_time(*args, **kwargs):
            start = perf_counter()
            result = func(*args, **kwargs)
            time_taken = perf_counter() - start
            return f"Function: {func.__name__} \nOutput: {result} \nTime taken: {time_taken:.4f} seconds."

        return exec_time


def cleanup_stuff(init=False):
    to_del = [
        "/usr/local/lib/python3.10/site-packages/pip/_vendor/.wh.appdirs.py",
        "/usr/local/lib/python3.10/site-packages/.wh.pip-22.0.4.dist-info",
        "/usr/local/lib/python3.10/site-packages/.wh.setuptools-58.1.0.dist-info",
    ]
    if init:
        to_del.extend(["jewel", "bird", ".wget-hsts", "prvenv"])
    osremove(to_del, folders=init, verbose=False)


def setTZ(TZ=None):
    try:
        from pytz import timezone
    except ImportError:
        print("Install 'pytz' module")
        return

    if not TZ:
        # TZ = udB.get_key("TIMEZONE")
        TZ = "Asia/Kolkata"
    try:
        timezone(TZ)
        environ["TZ"] = TZ
        tzset()
    except AttributeError as er:
        print(er)
    except BaseException:
        environ["TZ"] = "UTC"
        tzset()


def _user_specifics(Var, LOGS):
    if Var.HOST.lower() == "heroku":
        if environ.get("qBit"):
            LOGS.info("Starting qBittorrent Web-UI")
            system("bash 1337x &")


def do_pip_recursive(file_data):
    def checkr(txt):
        t = txt.strip()
        return t and not t.startswith("#")

    _data = filter(checkr, file_data.split("\n"))
    for reqs in _data:
        system("pip3 install -q --no-cache-dir " + reqs.strip())


def on_startup():
    import nest_asyncio

    setTZ()
    nest_asyncio.apply()
    load_dotenv(override=True)
    from .configs import Var

    if Var.HOST.lower() != "local":
        remove(".env")
    return time(), Var


def post_startup():
    from .startup.funcs import _version_changes, update_envs
    from .fns.multi_db import _init_multi_dbs
    from . import LOGS, udB, Var

    LOGS.debug("Post Startup -> Init")
    update_envs()
    _version_changes(udB)
    _user_specifics(Var, LOGS)
    _init_multi_dbs("MULTI_DB")
    cleanup_stuff(init=True)

    if Var.HOST.lower() == "heroku":
        from .heroku import herokuapp

        try:
            herokuapp(Var)
        except BaseException:
            LOGS.exception("pyUlt.Herokuapp error: ")

    LOGS.debug("Post Startup -> Done")
