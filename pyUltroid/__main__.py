# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import asyncio
import os
import sys
import time

from . import *


def main():
    from pyrog import _init_pyrog
    from .fns.helper import bash, time_formatter, updater
    from .startup.funcs import (
        WasItRestart,
        autopilot,
        customize,
        fetch_ann,
        plug,
        ready,
        startup_stuff,
    )
    from .startup.loader import load_other_plugins

    # Option to Auto Update On Restart..
    """
    if (
        udB.get_key("UPDATE_ON_RESTART")
        and os.path.exists(".git")
        and asst.run_in_loop(updater())
    ):
        asst.run_in_loop(bash("bash installer.sh"))
        os.execl(sys.executable, "python3", "-m", "pyUltroid")
    """

    LOGS.info("Initialising...")

    ultroid_bot.run_in_loop(startup_stuff())

    ultroid_bot.me.phone = None

    if not ultroid_bot.me.bot:
        udB.set_key("OWNER_ID", ultroid_bot.uid)

    ultroid_bot.run_in_loop(autopilot())

    # Starting Pyrogram..
    ultroid_bot.run_in_loop(_init_pyrog())

    pmbot = udB.get_key("PMBOT")
    manager = udB.get_key("MANAGER")
    addons = udB.get_key("ADDONS") or Var.ADDONS
    vcbot = udB.get_key("VCBOT") or Var.VCBOT
    if HOSTED_ON == "okteto":
        vcbot = False

    if (HOSTED_ON == "termux" or udB.get_key("LITE_DEPLOY")) and udB.get_key(
        "EXCLUDE_OFFICIAL"
    ) is None:
        _plugins = "autocorrect autopic audiotools compressor forcesubscribe fedutils gdrive glitch instagram nsfwfilter nightmode pdftools profanityfilter writer youtube"
        udB.set_key("EXCLUDE_OFFICIAL", _plugins)

    load_other_plugins(addons=addons, pmbot=pmbot, manager=manager, vcbot=vcbot)

    suc_msg = """{}
            ----------------------------------------------------------------------
                Ultroid has been deployed! Visit @TheUltroid for updates!!
            ----------------------------------------------------------------------
    """

    # for plugin channels
    plugin_channels = udB.get_key("PLUGIN_CHANNEL")

    # Customize Ultroid Assistant...
    # ultroid_bot.run_in_loop(customize())

    # Load Addons from Plugin Channels.
    if plugin_channels:
        ultroid_bot.run_in_loop(plug(plugin_channels))

    # add job to scheduler
    from pyUltroid.custom.functions import scheduler

    if scheduler:
        scheduler.add_job(fetch_ann, "interval", minutes=12 * 60)

    # Edit Restarting Message (if It's restarting)
    ultroid_bot.run_in_loop(WasItRestart(udB))

    # Send/Ignore Deploy Message..
    if not udB.get_key("LOG_OFF"):
        ultroid_bot.run_in_loop(ready())

    try:
        cleanup_cache()
    except BaseException:
        pass

    LOGS.info(
        suc_msg.format(
            f"Took {time_formatter((time.time() - start_time)*1000)} to start •ULTROID•"
        )
    )


async def init_shutdown():
    tasks = []
    if ultroid_bot.is_connected():
        tasks.append(ultroid_bot.disconnect())
    if not BOT_MODE:
        msgs = (
            ("#restart", "Restarting Bot")
            if udB.get_key("_RESTART")
            else ("#exiting", "Shutting Down")
        )
        await asst.send_message(
            udB.get_key("TAG_LOG"),
            f"{msgs[0]}\n#ultroid\n\n`{msgs[1]}..`",
        )
        tasks.append(asst.disconnect())
    await asyncio.sleep(5)
    await asyncio.gather(*tasks, return_exceptions=True)
    await loop.shutdown_asyncgens()


def shutdown_or_restart():
    sys.stdout.flush()
    if not udB.get_key("_RESTART"):
        sys.exit(0)
    time.sleep(8)
    python = sys.executable
    os.execl(python, python, "-m", "pyUltroid")


if __name__ == "__main__":
    try:
        main()
        loop.run_until_complete(ultroid_bot.disconnected)
    except BaseException as exc:
        LOGS.exception(exc)
    finally:
        LOGS.info("Stopping Ultroid..")
        loop.run_until_complete(init_shutdown())
        loop.stop()
        shutdown_or_restart()
