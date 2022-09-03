import os

from .. import LOGS, HOSTED_ON


def connect_single_db(data, type, petname, cache):
    from ..startup._database import MongoDB, RedisDB, SqlDB

    if type == "mongo":
        yay = MongoDB(data, naam=petname, to_cache=cache)
        if yay.ping():
            return yay
        else:
            return LOGS.error(f"Error in Connecting {petname}")

    elif type == "sql":
        name = "SQL: " + petname
        yay = SqlDB(data, name)
        if yay.ping():
            return yay
        else:
            return LOGS.error(f"Error in Connecting {petname}")

    elif type == "redis":
        name = "Redis: " + petname
        stuff = data.split()
        yay = RedisDB(
            host=stuff[1],
            password=stuff[0],
            port=None,
            naam=name,
            platform=HOSTED_ON,
            decode_responses=True,
            socket_timeout=5,
            retry_on_timeout=True,
            to_cache=cache,
        )
        if yay.ping():
            return yay
        else:
            return LOGS.error(f"Error in Connecting: {petname}")
    else:
        return LOGS.error("Invalid DB format: " + petname)


def _init_multi_dbs(var):
    from ast import literal_eval

    co = 0
    stuff = os.getenv(var)
    if not stuff:
        return LOGS.error(f"Var {var} is not filled.")
    del os.environ[var]
    data = literal_eval(str(stuff))
    for k, v in data.items():
        co += 1
        to_cache = False
        if type(v) is tuple:
            v, to_cache = v
        key = "udB" + str(co)
        if "redislabs.com" in v:
            _type = "redis"
        elif "mongodb" in v:
            _type = "mongo"
        else:
            _type = "sql"

        if cx := connect_single_db(v, _type, k, to_cache):
            LOGS.debug(f"MultiDB: {_type}, {k}")
            globals()[key] = cx
