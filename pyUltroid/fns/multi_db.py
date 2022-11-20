import os

from .. import LOGS, HOSTED_ON


def _connect_single_db(data, type, petname, cache):
    from ..startup._database import MongoDB, RedisDB, SqlDB

    if type == "mongo":
        name = "Mongo: " + petname
        yay = MongoDB(key=data, _name=name, to_cache=cache)
        if yay.ping():
            return yay
        else:
            return LOGS.error(f"Error in Connecting {petname}")

    elif type == "sql":
        name = "Sql: " + petname
        yay = SqlDB(url=data, _name=name, to_cache=cache)
        if yay.ping():
            return yay
        else:
            return LOGS.error(f"Error in Connecting {petname}")

    else:  # Redis
        name = "Redis: " + petname
        stuff = data.split()
        yay = RedisDB(
            host=stuff[1],
            password=stuff[0],
            port=None,
            _name=name,
            platform=HOSTED_ON,
            decode_responses=True,
            socket_timeout=6,
            retry_on_timeout=True,
            to_cache=cache,
        )
        if yay.ping():
            return yay
        else:
            return LOGS.error(f"Error in Connecting: {petname}")


def _init_multi_dbs(var):
    from ast import literal_eval

    co = 0
    stuff = os.getenv(var)
    if not stuff:
        return LOGS.error(f"Var {var} is not filled.")
    del os.environ[var]
    data = literal_eval(str(stuff))
    dct = {}
    for k, v in data.items():
        co += 1
        to_cache = False
        if type(v) in (tuple, list):
            v, to_cache = v
        key = "udB" + str(co)
        if "redislabs" in v:
            _type = "redis"
        elif "mongodb" in v:
            _type = "mongo"
        else:
            _type = "sql"

        if cx := _connect_single_db(v, _type, k, to_cache):
            dct[len(dct) + 1] = f"{k} -> {_type}"
            globals()[key] = cx

    if dct:
        from .tools import json_parser

        LOGS.debug(json_parser(dct, indent=2))
