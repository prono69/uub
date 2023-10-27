import os
from random import randrange

from redis.exceptions import ConnectionError, TimeoutError

from pyUltroid import udB, Var
from pyUltroid.startup import HOSTED_ON, LOGS
from pyUltroid.startup._database import MongoDB, RedisDB, SqlDB


def _connect_single_db(data, type, petname, cache):
    if type == "mongo":
        name = "Mongo: " + petname
        try:
            return MongoDB(key=data, _name=name, to_cache=cache)
        except Exception:
            LOGS.warning(f"MultiDB: Error while Connecting to MongoDB: {petname}")
            return LOGS.debug("", exc_info=True)

    elif type == "sql":
        name = "Sql: " + petname
        try:
            return SqlDB(url=data, _name=name, to_cache=cache)
        except Exception:
            LOGS.warning(f"MultiDB: Error while Connecting to SQL DB: {petname}")
            return LOGS.debug("", exc_info=True)

    else:
        name = "Redis: " + petname
        stuff = data.split()
        try:
            return RedisDB(
                host=stuff[1],
                password=stuff[0],
                port=None,
                _name=name,
                platform=HOSTED_ON,
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True,
                to_cache=cache,
            )
        except (ConnectionError, TimeoutError):
            LOGS.warning(f"MultiDB: Error while Connecting to RedisDB: {petname}")
            return LOGS.debug("", exc_info=True)
        except Exception as exc:
            return LOGS.exception(exc)


def _init_multi_dbs(var):
    from ast import literal_eval

    stuff = os.getenv(var)
    if not stuff:
        return LOGS.warning(f"Var '{var}' not found; not loading multi DB..")

    LOGS.info("Loading Multi DB's..")
    if Var.HOST.lower() == "heroku":
        os.environ.pop(var, None)
    count = 0
    multi_db = {}
    all_dbs = literal_eval(stuff)
    for name, data in all_dbs.items():
        count += 1
        to_cache = False
        redis_instance = "udB" + str(count)
        if type(data) in (tuple, list):
            to_cache = data[1] == True
            data = data[0]
        if data == "self":
            multi_db[count] = f"{name} -> self"
            globals()[redis_instance] = udB
            continue
        if "redislabs" in data:
            db_type = "redis"
        elif "mongodb" in data:
            db_type = "mongo"
        else:
            db_type = "sql"

        if DB := _connect_single_db(data, db_type, name, to_cache):
            try:
                if randrange(100) > 75:
                    DB.del_key("__nocache__")
            except Exception as exc:
                LOGS.warning(f"MultiDB: Error in {name}")
                LOGS.debug(exc, exc_info=True)
                continue

            multi_db[count] = f"{name} -> {db_type}"
            globals()[redis_instance] = DB

    if multi_db:
        from pyUltroid.fns.tools import json_parser

        LOGS.debug(json_parser(multi_db, indent=2))
        LOGS.info("Loaded all DB's!")
