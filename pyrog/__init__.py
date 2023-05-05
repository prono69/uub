# this is not a Copyrighted material
# @spemgod | @ah3h3
#
# Obv this is just for personal use.
# bcz telethon is slow in download and upload.
#
# And em, dont kang this? maybe :)
# jk, do whatever tf u want, idc
#
# Edited on 13-05-2022 // for pyrogram v2.
# 28-06-2022 // added asyncio.gather for faster startup.


import asyncio
from ast import literal_eval
from copy import deepcopy
from os import getcwd, environ

from pyrogram import Client
from pyUltroid import LOGS
from pyUltroid.configs import Var


PYROG_CLIENTS = {}
_default_client_values = {
    "api_id": Var.API_ID,
    "api_hash": Var.API_HASH,
    "workdir": getcwd() + "/resources/temp",
    "sleep_threshold": 60,
    "workers": 6,
    "no_updates": True,
}


def app(n=None):
    _default = PYROG_CLIENTS.get(1)
    return PYROG_CLIENTS.get(n, _default) if n else _default


def get_clients():
    # plugins = {"root": "pyrog/plugins"}
    var = "PYROGRAM_CLIENTS"
    stuff = environ.get(var)
    if not stuff:
        LOGS.warning(
            "'PYROGRAM_CLIENTS' ENV wasn't found, Skipping PyroGram Initialisation."
        )
        return True
    data = literal_eval(stuff)
    if Var.HOST.lower() == "heroku":
        environ.pop(var, None)
    for k, v in data.items():
        _default = deepcopy(_default_client_values)
        _default.update({"name": "bot_" + str(k)})
        if type(v) == dict:
            _default |= v
        else:
            _default.update({"bot_token": v})
        PYROG_CLIENTS.update({int(k): Client(**_default)})


async def start(count, client):
    try:
        await client.start()
    except Exception:
        LOGS.exception(f"Error while starting Client: {count}")
        PYROG_CLIENTS.pop(count, None)


async def _init_pyrog():
    LOGS.info("Starting Pyrogram...")
    if get_clients():
        return
    await asyncio.gather(
        *[start(count, client) for count, client in PYROG_CLIENTS.copy().items()]
    )
    return LOGS.info(
        f"{len(PYROG_CLIENTS)} Clients Running -> {tuple(PYROG_CLIENTS.keys())}"
    )
