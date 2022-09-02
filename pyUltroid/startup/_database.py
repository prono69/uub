# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import os
import sys
from ast import literal_eval
from copy import deepcopy

from ..configs import Var
from . import *


Redis = MongoClient = psycopg2 = Database = None
if (Var.REDIS_URI or Var.REDISHOST):
    try:
        from redis import Redis
    except ImportError:
        LOGS.info("Installing 'redis' for database.")
        os.system("pip3 install -q redis hiredis")
        from redis import Redis

elif Var.MONGO_URI:
    try:
        from pymongo import MongoClient
    except ImportError:
        LOGS.info("Installing 'pymongo' for database.")
        os.system("pip3 install -q pymongo[srv]")
        from pymongo import MongoClient

elif Var.DATABASE_URL:
    try:
        import psycopg2
    except ImportError:
        LOGS.info("Installing 'pyscopg2' for database.")
        os.system("pip3 install -q psycopg2-binary")
        import psycopg2

else:
    try:
        from localdb import Database
    except ImportError:
        LOGS.info("Using local file as database.")
        os.system("pip3 install -q localdb.json")
        from localdb import Database

# --------------------------------------------------------------------------------------------- #


class _BaseDatabase:
    def __init__(self, *args, **kwargs):
        self._cache = {}

    def ping(self):
        return 1

    @property
    def usage(self):
        return 0

    def keys(self):
        return []

    def del_key(self, key):
        if self.to_cache:
            self._cache.pop(key, None)
        self.delete(key)
        return True

    def _get_data(self, key=None, data=None):
        if key:
            try:
                data = self.get(str(key))
            except:
                return "Wrong.Value.TypeError"
        if data:
            try:
                data = literal_eval(str(data))
            except BaseException:
                pass
        return data

    def re_cache(self, key=None):
        if not self.to_cache:
            raise TypeError("Caching is disabled")
        if key:
            self._cache.pop(key, None)
            if data := self.get_key(key, force=True):
                self._cache[key] = data
                return True
            return "Key not found"
        for key in self.keys():
            self._cache.update({key: self.get_key(key, force=True)})

    def get_key(self, key, force=False):
        if not self.to_cache:
            if key in self.keys():
                return self._get_data(key=key)
        elif key in self._cache:
            return deepcopy(self._cache[key])
        elif force:
            if key in self.keys():
                value = self._get_data(key=key)
                self._cache.update({key: value})
                return deepcopy(value)

    def set_key(self, key, value):
        value = self._get_data(data=value)
        if self.to_cache:
            self._cache.update({key: value})
        self.set(str(key), str(value))
        return True

    def rename(self, key1, key2):
        if val := self.get_key(key1, force=True):
            self.del_key(key1)
            return self.set_key(key2, val)
        return False

    def append(self, key, value):
        if not (data := self.get_key(key)):
            return "Key doesn't exists!"
        value = self._get_data(data=value)
        if type(data) == set:
            data.add(value)
        elif type(data) == dict:
            data = data | value
        elif type(data) == list:
            data.append(value)
        elif type(data) == tuple:
            lst = list(data)
            lst.append(value)
            data = tuple(lst)
        else:
            data += " " + str(value)
        return self.set_key(key, data)

# --------------------------------------------------------------------------------------------- #


class MongoDB(_BaseDatabase):
    def __init__(self, key, to_cache, name, dbname="UltroidDB"):
        self.dB = MongoClient(key, serverSelectionTimeoutMS=5000)
        self.db = self.dB[dbname]
        self.to_cache = to_cache
        self.name = name
        super().__init__()

    def __repr__(self):
        return f"<Ultroid.MonGoDB\n -total_keys: {len(self.keys())}\n>"

    @property
    def name(self):
        return self.name

    @property
    def usage(self):
        return self.db.command("dbstats")["dataSize"]

    def ping(self):
        if self.dB.server_info():
            return True

    def keys(self):
        return self.db.list_collection_names()

    def set_key(self, key, value):
        value = self._get_data(data=value)
        if key in self.keys():
            self.db[key].replace_one({"_id": key}, {"value": str(value)})
        else:
            self.db[key].insert_one({"_id": key, "value": str(value)})
        if self.to_cache:
            self._cache.update({key: value})
        return True

    def delete(self, key):
        if self.to_cache:
            self._cache.pop(key, None)
        if key in self.keys():
            self.db.drop_collection(key)
            return True

    def get(self, key):
        if x := self.db[key].find_one({"_id": key}):
            return x["value"]


"""
def flushall(self):
        self.dB.drop_database("UltroidDB")
        self._cache.clear()
        return True
"""

# --------------------------------------------------------------------------------------------- #


# Thanks to "Akash Pattnaik" / @BLUE-DEVIL1134
# for SQL Implementation in Ultroid.
#
# Please use https://elephantsql.com/ !

class SqlDB(_BaseDatabase):
    def __init__(self, url, to_cache, name="SQL_DB"):
        self._connection = None
        self._cursor = None
        self.url = url
        self.to_cache = to_cache
        self.name = name
        try:
            self._connection = psycopg2.connect(dsn=url)
            self._connection.autocommit = True
            self._cursor = self._connection.cursor()
            self._cursor.execute(
                "CREATE TABLE IF NOT EXISTS Ultroid (ultroidCli varchar(70))"
            )
        except Exception as error:
            LOGS.exception(error)
            LOGS.info("Invaid SQL Database")
            if self._connection:
                self._connection.close()
            sys.exit()
        super().__init__()

    @property
    def name(self):
        return self.name

    @property
    def usage(self):
        self._cursor.execute(
            "SELECT pg_size_pretty(pg_relation_size('Ultroid')) AS size"
        )
        data = self._cursor.fetchall()
        return int(data[0][0].split()[0])

    def keys(self):
        self._cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name  = 'ultroid'"
        )  # case sensitive
        data = self._cursor.fetchall()
        return [_[0] for _ in data]

    def get(self, variable):
        try:
            self._cursor.execute(f"SELECT {variable} FROM Ultroid")
        except psycopg2.errors.UndefinedColumn:
            return None
        data = self._cursor.fetchall()
        if not data:
            return None
        if len(data) >= 1:
            for i in data:
                if i[0]:
                    return i[0]

    def set(self, key, value):
        try:
            self._cursor.execute(f"ALTER TABLE Ultroid DROP COLUMN IF EXISTS {key}")
        except (psycopg2.errors.UndefinedColumn, psycopg2.errors.SyntaxError):
            pass
        except BaseException as er:
            LOGS.exception(er)
        self._cache.update({key: value})
        self._cursor.execute(f"ALTER TABLE Ultroid ADD {key} TEXT")
        self._cursor.execute(f"INSERT INTO Ultroid ({key}) values (%s)", (str(value),))
        return True

    def delete(self, key):
        try:
            self._cursor.execute(f"ALTER TABLE Ultroid DROP COLUMN {key}")
        except psycopg2.errors.UndefinedColumn:
            return False
        return True


"""
def flushall(self):
    self._cache.clear()
    self._cursor.execute("DROP TABLE Ultroid")
    self._cursor.execute(
        "CREATE TABLE IF NOT EXISTS Ultroid (ultroidCli varchar(70))"
    )
    return True
"""

# --------------------------------------------------------------------------------------------- #


class RedisDB(_BaseDatabase):
    def __init__(
        self,
        host,
        port,
        password,
        to_cache,
        platform="",
        name="RedisDB",
        logger=LOGS,
        *args,
        **kwargs,
    ):
        if host and ":" in host:
            spli_ = host.split(":")
            host = spli_[0]
            port = int(spli_[-1])
            if host.startswith("http"):
                logger.error("Your REDIS_URI should not start with http !")
                import sys

                sys.exit()
        elif not host or not port:
            logger.error("Port Number not found")
            import sys

            sys.exit()

        kwargs["host"] = host
        kwargs["password"] = password
        kwargs["port"] = port

        if platform.lower() == "qovery" and not host:
            var, hash_, host, password = "", "", "", ""
            for vars_ in os.environ:
                if vars_.startswith("QOVERY_REDIS_") and vars.endswith("_HOST"):
                    var = vars_
            if var:
                hash_ = var.split("_", maxsplit=2)[1].split("_")[0]
            if hash:
                kwargs["host"] = os.environ(f"QOVERY_REDIS_{hash_}_HOST")
                kwargs["port"] = os.environ(f"QOVERY_REDIS_{hash_}_PORT")
                kwargs["password"] = os.environ(f"QOVERY_REDIS_{hash_}_PASSWORD")

        self.db = Redis(**kwargs)
        self.set = self.db.set
        self.get = self.db.get
        self.keys = self.db.keys
        self.delete = self.db.delete
        self.to_cache = to_cache
        self.name = name
        super().__init__()

    @property
    def name(self):
        return self.name

    @property
    def usage(self):
        return sum(self.db.memory_usage(x) for x in self.keys())

    def real(self, key):
        try:
            return self.db.get(key)
        except:
            try:
                return self.db.lrange(key, 0, -1)
            except:
                return self.db.hgetall(key)

# --------------------------------------------------------------------------------------------- #


class LocalDB(_BaseDatabase):
    def __init__(self):
        self.db = Database("ultroid")
        self.name = "LocalDB"
        self.to_cache = True
        super().__init__()

    def keys(self):
        return self._cache.keys()

    def __repr__(self):
        return f"<Ultroid.LocalDB\n -total_keys: {len(self.keys())}\n>"

# --------------------------------------------------------------------------------------------- #


def UltroidDB():
    _er = False
    from .. import HOSTED_ON

    try:
        if Redis:
            return RedisDB(
                host=Var.REDIS_URI or Var.REDISHOST,
                password=Var.REDIS_PASSWORD or Var.REDISPASSWORD,
                port=Var.REDISPORT,
                platform=HOSTED_ON,
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True,
            )
        if MongoClient:
            return MongoDB(Var.MONGO_URI)
        if psycopg2:
            return SqlDB(Var.DATABASE_URL)
    except BaseException as err:
        LOGS.exception(err)
        _er = True
    if not _er:
        LOGS.critical(
            "No DB requirement fullfilled!\nPlease install redis, mongo or sql dependencies...\nTill then using local file as database."
        )
    if HOSTED_ON == "termux":
        return LocalDB()
    exit()

# --------------------------------------------------------------------------------------------- #
