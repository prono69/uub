from pyUltroid import udB, ultroid_bot as ult

_RKEY = udB.get_key("_PYROGRAM")
_HANDLERS = _RKEY.get("handlers", "?")
_AUTH_USERS = _RKEY.get("users", ult.uid)
