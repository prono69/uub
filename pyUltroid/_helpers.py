# some custom helper functions

from dotenv import load_dotenv
from os import environ, path, remove, system
from time import time, tzset


def osremove(*args, folders=False, verbose=False):
    from shutil import rmtree
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


def cleanup_stuff(init=False):
    to_del = [
        "/usr/local/lib/python3.10/site-packages/pip/_vendor/.wh.appdirs.py",
        "/usr/local/lib/python3.10/site-packages/.wh.pip-22.0.4.dist-info",
        "/usr/local/lib/python3.10/site-packages/.wh.setuptools-58.1.0.dist-info",
    ]
    if init:
        to_del.extend(
            ["jewel", "bird", ".env", ".wget-hsts"],
        )
    osremove(to_del, folders=init, verbose=False)


def settz(TZ="Asia/Kolkata"):
    try:
        from pytz import timezone
    except ImportError:
        print("Install 'pytz' module")
        return

    # TZ = udB.get_key("TIMEZONE")
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
    if Var.USER.lower() == "dotarc":
        if Var.HOST.lower() == "heroku":
            LOGS.info("Starting qBittorrent Web-UI")
            system("bash 1337x &")
            # LOGS.debug("Updating pip")
            # system("wget -q -O getpip.py https://bootstrap.pypa.io/get-pip.py && python3 getpip.py &> /dev/null")

    elif Var.USER.lower() == "aprish" and Var.HOST.lower() == "heroku":
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
    _time = time()
    load_dotenv()
    settz(TZ="Asia/Kolkata")
    from .configs import Var

    if Var.HOST.lower() == "wfs":
        load_dotenv("prvenv")
        remove("prvenv")
    return _time, Var


def post_startup():
    from .startup.funcs import _version_changes
    from .functions.multi_db import _init_multi_dbs
    from . import LOGS, udB, Var

    _version_changes(udB)
    _user_specifics(Var, LOGS)
    _init_multi_dbs("MULTI_DB")
    cleanup_stuff(init=True)

    if Var.HOST.lower() == "heroku":
        from .heroku import herokuapp

        try:
            herokuapp(Var)
        except BaseException:
            LOGS.exception("pyUlt.herokuapp error: ")
