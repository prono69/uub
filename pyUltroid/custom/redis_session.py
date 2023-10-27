# https://github.com/ezdev128/telethon-session-redis
# pypi - teleredis

from collections import UserDict
from enum import Enum
import datetime
import time

from telethon import utils
from telethon.tl import types
from telethon.crypto import AuthKey
from telethon.sessions import Session
from telethon.tl import TLObject
from telethon.tl.types import (
    PeerUser,
    PeerChat,
    PeerChannel,
    InputPeerUser,
    InputPeerChat,
    InputPeerChannel,
    InputPhoto,
    InputDocument,
)

from pyUltroid.startup import LOGS


# from session/memorysession
class _SentFileType(Enum):
    DOCUMENT = 0
    PHOTO = 1

    @staticmethod
    def from_type(cls):
        if cls == InputDocument:
            return _SentFileType.DOCUMENT
        elif cls == InputPhoto:
            return _SentFileType.PHOTO
        else:
            raise ValueError("The cls must be either InputDocument/InputPhoto")


class LRUCache(UserDict):
    """
    LRU (Least Recently Used) cache Implementation.
    """

    __slots__ = ("maxsize", "data")

    def __init__(self, *args, **kwargs):
        self.maxsize = kwargs.pop("maxsize", 128)
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        if value := self.data.get(key):
            self.data.pop(key, None)
            self.data[key] = value
            return value

    def __setitem__(self, key, value):
        self.data[key] = value
        while len(self.data) > self.maxsize:
            self.data.pop(next(iter(self.data)))


class RedisSession(Session):
    __slots__ = (
        "redis",
        "key",
        "save_entities",
        "_dc_id",
        "_server_address",
        "_port",
        "_auth_key",
        "_takeout_id",
    )

    def __init__(self, redis, key_name, save_entities=True):
        super().__init__()

        self._dc_id = 0
        self._server_address = None
        self._port = None
        self._auth_key = None
        self._takeout_id = None

        self._lrucache = LRUCache(maxsize=128)
        self.redis = redis
        self.key = key_name
        self.save_entities = True
        self.feed_session()

    # Property

    @property
    def dc_id(self):
        return self._dc_id

    @property
    def server_address(self):
        return self._server_address

    @property
    def port(self):
        return self._port

    @property
    def auth_key(self):
        return self._auth_key

    @property
    def takeout_id(self):
        return self._takeout_id

    # Helper functions from MemorySession

    @staticmethod
    def _entity_values_to_row(id, hash, username, phone, name):
        # While this is a simple implementation it might be overrode by,
        # other classes so they don't need to implement the plural form
        # of the method. Don't remove.
        return id, hash, username, phone, name

    def _entity_to_row(self, e):
        if not isinstance(e, TLObject):
            return
        try:
            p = utils.get_input_peer(e, allow_self=False)
            marked_id = utils.get_peer_id(p)
        except TypeError:
            # Note: `get_input_peer` already checks for non-zero `access_hash`.
            #        See issues #354 and #392. It also checks that the entity
            #        is not `min`, because its `access_hash` cannot be used
            #        anywhere (since layer 102, there are two access hashes).
            return

        if isinstance(p, (InputPeerUser, InputPeerChannel)):
            p_hash = p.access_hash
        elif isinstance(p, InputPeerChat):
            p_hash = 0
        else:
            return

        username = getattr(e, "username", None) or None
        if username is not None:
            username = username.lower()
        phone = getattr(e, "phone", None)
        name = utils.get_display_name(e) or None
        return self._entity_values_to_row(marked_id, p_hash, username, phone, name)

    def _entities_to_rows(self, tlo):
        if not isinstance(tlo, TLObject) and utils.is_list_like(tlo):
            # This may be a list of users already for instance
            entities = tlo
        else:
            entities = []
            if hasattr(tlo, "user"):
                entities.append(tlo.user)
            if hasattr(tlo, "chat"):
                entities.append(tlo.chat)
            if hasattr(tlo, "chats") and utils.is_list_like(tlo.chats):
                entities.extend(tlo.chats)
            if hasattr(tlo, "users") and utils.is_list_like(tlo.users):
                entities.extend(tlo.users)

        rows = []  # Rows to add (id, hash, username, phone, name)
        for e in entities:
            if row := self._entity_to_row(e):
                rows.append(row)
        return rows

    # Custom Helper functions

    def _do_eval(self, data):
        value = self.redis._get_data(data=data)
        # if type(value) == dict:
        # value.pop("saved_time", None)
        return value

    def _get_data(self, key):
        if val := self._lrucache.get(key):
            return val

        try:
            value = self.redis.db.hget(self.key, key)
            value = self._do_eval(value)
            self._lrucache[key] = value
            return value
        except Exception as exc:
            return LOGS.exception(exc)

    """
    # for 'saved_time'

    time.strftime("%F %T") -> '2022-08-14 11:45:34'
    x = time.strptime("2022-08-14 11:45:34", "%Y-%m-%d %H:%M:%D")
    x -> time.struct_time(tm_year=2022, tm_mon)...
    y = time.mktime(x) -> 1656282648.0
    datetime.datetime.fromtimestamp(y) -> datetime object
    """

    def _save_data(self, key, value):
        self._lrucache[key] = value
        if type(value) == dict:
            value["saved_time"] = time.strftime("%F %T", time.localtime())
        try:
            return self.redis.db.hset(self.key, key, str(value))
        except Exception as exc:
            return LOGS.exception(exc)

    def _get_dict_items(self, pattern, fix_values=True):
        try:
            _, entities = self.redis.db.hscan(self.key, 0, pattern)
            if fix_values:
                for k, v in entities.copy().items():
                    entities[k] = self._do_eval(v)
            return entities
        except Exception as exc:
            LOGS.exception(exc)
            return {}

    # To Do's

    def clone(self, to_instance):
        raise NotImplementedError

    def delete(self, key):
        # return self.db.hdel(self.key, key)
        raise NotImplementedError

    def close(self):
        # todo: save in memory cache to database
        self.clear_cache()

    def save(self, to_instance=None):
        pass

    # Initialisation

    def feed_session(self):
        try:
            sess = self._get_sessions()
            if len(sess) == 0:
                self._auth_key = AuthKey(data=b"")
                return

            data = self._get_data(sess[-1])
            if not data:
                # No sessions
                self._auth_key = AuthKey(data=b"")
                return

            self._dc_id = data["dc_id"]
            self._server_address = data["server_address"]
            self._port = data["port"]
            auth_key = data.get("auth_key", b"")
            self._auth_key = AuthKey(data=auth_key)
            self._takeout_id = data["takeout_id"]
        except Exception as exc:
            LOGS.exception(exc)

    # Update session table

    def _update_session_table(self):
        """Stores session into redis."""
        auth_key = self._auth_key.key if self._auth_key else b""
        data = {
            "dc_id": self._dc_id,
            "server_address": self._server_address,
            "port": self._port,
            "auth_key": auth_key,
            "takeout_id": self._takeout_id,
        }
        self._save_data(f"sessions:{self._dc_id}", data)

    # Update State

    def get_update_state(self, entity_id):
        if data := self._get_data(f"update_state:{entity_id}"):
            timestamp = datetime.datetime.fromtimestamp(date, tz=datetime.timezone.utc)
            return types.updates.State(
                data["pts"], data["qts"], data["date"], data["seq"], unread_count=0
            )

    def set_update_state(self, entity_id, state):
        data = {
            "id": entity_id,
            "pts": state.pts,
            "qts": state.qts,
            "date": state.date.timestamp(),
            "seq": state.seq,
        }
        self._save_data(f"update_state:{entity_id}", data)

    def get_update_states(self):
        try:
            entities = self._get_dict_items(pattern="update_state:*")
            return (
                (
                    entity["id"],
                    types.updates.State(
                        pts=entity["pts"],
                        qts=entity["qts"],
                        date=datetime.datetime.fromtimestamp(
                            entity["date"], tz=datetime.timezone.utc
                        ),
                        seq=entity["seq"],
                        unread_count=0,
                    ),
                )
                for entity in entities.values()
            )
        except Exception as exc:
            LOGS.exception(exc)

    # Configs

    def clear_cache(self):
        self._lrucache.clear()

    @takeout_id.setter
    def takeout_id(self, value):
        self._takeout_id = value
        self._update_session_table()

    @auth_key.setter
    def auth_key(self, value):
        self._auth_key = value
        self._update_session_table()

    def set_dc(self, dc_id, server_address, port):
        """
        Sets the information of the data center address and port that
        the library should connect to, as well as the data center ID,
        which is currently unused.
        """
        self._dc_id = dc_id or 0
        self._server_address = server_address
        self._port = port

        self._update_session_table()

        data = self._get_data(f"sessions:{self._dc_id}")
        self._auth_key = AuthKey(data=data.get("auth_key", None))

    def list_sessions(self):
        """
        Lists available sessions. Not used by the library itself.
        """
        return self._get_sessions(clean_prefix=True)

    # Entity processing

    # from MemorySession
    def get_input_entity(self, key):
        try:
            if key.SUBCLASS_OF_ID in (0xC91C90B6, 0xE669BF46, 0x40F202FD):
                # hex(crc32(b'InputPeer', b'InputUser' and b'InputChannel'))
                # We already have an Input version, so nothing else required
                return key
            # Try to early return if this key can be casted as input peer
            return utils.get_input_peer(key)
        except (AttributeError, TypeError):
            # Not a TLObject or can't be cast into InputPeer
            if isinstance(key, TLObject):
                key = utils.get_peer_id(key)
                exact = True
            else:
                exact = not isinstance(key, int) or key < 0

        result = None
        if isinstance(key, str):
            if phone := utils.parse_phone(key):
                result = self.get_entity_rows_by_phone(phone)
            else:
                username, invite = utils.parse_username(key)
                if username and not invite:
                    result = self.get_entity_rows_by_username(username)
                elif tup := utils.resolve_invite_link(key)[1]:
                    result = self.get_entity_rows_by_id(tup, exact=False)

        elif isinstance(key, int):
            result = self.get_entity_rows_by_id(key, exact)

        if not result and isinstance(key, str):
            result = self.get_entity_rows_by_name(key)

        if not result:
            raise ValueError("Could not find input entity with key ", key)
        entity_id, entity_hash = result  # unpack resulting tuple
        entity_id, kind = utils.resolve_id(entity_id)
        # removes the mark and returns type of entity
        if kind == PeerUser:
            return InputPeerUser(entity_id, entity_hash)
        elif kind == PeerChat:
            return InputPeerChat(entity_id)
        elif kind == PeerChannel:
            return InputPeerChannel(entity_id, entity_hash)

    def process_entities(self, tlo):
        """
        Processes the input ``TLObject`` or ``list`` and saves
        whatever information is relevant (e.g., ID or access hash).
        """
        if not self.save_entities:
            return
        if not (rows := self._entities_to_rows(tlo)):
            return

        for row in rows:
            try:
                data = {
                    "id": row[0],
                    "hash": row[1],
                    "username": row[2],
                    "phone": row[3],
                    "name": row[4],
                }
                self._save_data(f"entities:{row[0]}", data)
            except Exception as exc:
                LOGS.exception(exc)

    def _get_entities(self, clean_prefix=False):
        """
        Returns list of entities keys in database.
        """
        try:
            entities = self._get_dict_items(pattern="entities:*", fix_values=False)
            keys = list(entities.keys())
            return keys if not clean_prefix else [key[9:] for key in keys]
        except Exception as exc:
            LOGS.exception(exc)
            return []

    def _get_sessions(self, clean_prefix=False):
        """
        Returns list of session keys in database.
        """
        try:
            sessions = self._get_dict_items(pattern="sessions:*", fix_values=False)
            keys = list(sessions.keys())
            return keys if not clean_prefix else [key[9:] for key in keys]
        except Exception as exc:
            LOGS.exception(exc)
            return []

    def _scan_db(self, dict_key, value):
        func = lambda x: x in value if utils.is_list_like(value) else x == value
        try:
            data = self._get_dict_items(pattern="entities:*")
            for entity in data.values():
                if func(entity.get(dict_key)):
                    return entity["id"], entity["hash"]
        except Exception as exc:
            return LOGS.exception(exc)

    def get_entity_rows_by_phone(self, phone):
        return self._scan_db("phone", phone)

    def get_entity_rows_by_username(self, username):
        return self._scan_db("username", username)

    def get_entity_rows_by_name(self, name):
        return self._scan_db("name", name)

    def get_entity_rows_by_id(self, entity_id, exact=True):
        if exact:
            data = self._get_data(f"entities:{entity_id}")
            return (entity_id, data["hash"]) if data else None

        ids = (
            utils.get_peer_id(PeerUser(entity_id)),
            utils.get_peer_id(PeerChat(entity_id)),
            utils.get_peer_id(PeerChannel(entity_id)),
        )
        return self._scan_db("id", ids)

    # File processing

    def get_file(self, md5_digest, file_size, cls):
        if data := self._get_data(f"sent_files:{md5_digest}"):
            if (
                data["md5_digest"] == md5_digest
                and data["file_size"] == file_size
                and data["type"] == _SentFileType.from_type(cls).value
            ):
                return cls(data["id"], data["hash"])

    def cache_file(self, md5_digest, file_size, instance):
        if not isinstance(instance, (InputDocument, InputPhoto)):
            raise TypeError(f"Cannot cache {type(instance)} instances!")

        try:
            data = {
                "md5_digest": md5_digest,
                "file_size": file_size,
                "type": _SentFileType.from_type(type(instance)).value,
                "id": instance.id,
                "hash": instance.access_hash,
            }
            self._save_data(f"sent_files:{md5_digest}", data)
        except Exception as exc:
            return LOGS.exception(exc)
