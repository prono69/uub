# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

__all__ = ("load_other_plugins",)

import os
import subprocess
import sys
from shutil import rmtree

from decouple import config

from . import *
from .utils import load_addons
from pyUltroid import *
from pyUltroid.dB._core import HELP
from pyUltroid.loader import Loader


def _after_load(loader, module, plugin_name=""):
    if not module or plugin_name.startswith("_"):
        return

    from strings import get_help

    if doc_ := get_help(plugin_name) or module.__doc__:
        try:
            doc = doc_.format(i=HNDLR)
        except Exception:
            return loader._logger.exception(
                f"{plugin_name} - {module}: Error in loading __doc__ or get_help!"
            )

        try:
            HELP[loader.key][plugin_name] = doc
        except KeyError:
            HELP[loader.key] = {plugin_name: doc}
        except Exception:
            loader._logger.exception(
                f"Error in adding __doc__ of {plugin_name} to HELP!"
            )


def load_other_plugins(addons=None, pmbot=None, manager=None, vcbot=None):
    # for official
    _exclude = (
        udB.get_key("EXCLUDE_OFFICIAL")
        or udB.get_key("__EXCLUDE_OFFICIAL", force=True)
        or config("EXCLUDE_OFFICIAL", None)
    )
    _exclude = _exclude.split() if _exclude else []

    # "INCLUDE_ONLY" was added to reduce Big List in "EXCLUDE_OFFICIAL" Plugin
    _in_only = udB.get_key("INCLUDE_ONLY") or config("INCLUDE_ONLY", None)
    _in_only = _in_only.split() if _in_only else []
    Loader().load(include=_in_only, exclude=_exclude, after_load=_after_load)

    # for assistant
    if not USER_MODE and not udB.get_key("DISABLE_AST_PLUGINS"):
        _ast_exc = ["pmbot"]
        if _in_only and "games" not in _in_only:
            _ast_exc.append("games")
        Loader(path="assistant").load(
            log=False,
            exclude=_ast_exc,
            after_load=_after_load,
        )

    # for addons
    if addons:

        def _fetch_addons():
            url = (
                udB.get_key("ADDONS_URL")
                or "https://github.com/TeamUltroid/UltroidAddons.git"
            )
            subprocess.run(f"git clone -q {url} addons", shell=True)

        if not os.path.isdir("addons"):
            _fetch_addons()
        if not os.path.isdir("addons/.git"):
            rmtree("addons", ignore_errors=True)
            _fetch_addons()
        else:
            subprocess.run("(cd addons && git pull --rebase)", shell=True)

        """
        if os.path.exists("addons/addons.txt"):
            # generally addons req already there so it won't take much time
            # subprocess.run(
            #        "rm -rf /usr/local/lib/python3.*/site-packages/pip/_vendor/.wh*"
            #    )
            subprocess.run(
                f"{sys.executable} -m pip install --no-cache-dir -q -r ./addons/addons.txt",
                shell=True,
            )
        """

        _exclude = udB.get_key("EXCLUDE_ADDONS") or udB.get_key(
            "__EXCLUDE_ADDONS", force=True
        )
        _exclude = _exclude.split() if _exclude else []
        _in_only = udB.get_key("INCLUDE_ADDONS")
        _in_only = _in_only.split() if _in_only else []

        Loader(path="addons", key="Addons").load(
            func=load_addons,
            include=_in_only,
            exclude=_exclude,
            after_load=_after_load,
            load_all=True,
        )

    if not USER_MODE:
        # group manager
        if manager:
            Loader(path="assistant/manager", key="Group Manager").load()

        # chat via assistant
        if pmbot:
            Loader(path="assistant/pmbot.py").load(log=False)

    # vc bot
    if vcbot and not vcClient._bot:
        try:
            import pytgcalls  # ignore: pylint
        except ImportError:
            return LOGS.error("'pytgcalls' not installed!\nSkipping loading of VCBOT.")

        if os.path.exists("vcbot"):
            if os.path.exists("vcbot/.git"):
                subprocess.run("(cd vcbot && git pull --rebase)", shell=True)
        else:
            subprocess.run(
                "git clone https://github.com/TeamUltroid/VcBot vcbot",
                shell=True,
            )
        try:
            os.makedirs("vcbot/downloads", exist_ok=True)
            Loader(path="vcbot", key="VCBot").load(after_load=_after_load)
        except (FileNotFoundError, Exception) as exc:
            LOGS.error(f"Skipping VCBot Installation - {exc}")
