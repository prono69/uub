# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

__all__ = (
    "HOSTED_ON",
    "KEEP_SAFE",
    "LOGS",
    "call_back",
    "cleanup_cache",
    "TelethonLogger",
    "where_hosted",
)

from ._logger import (
    LOGS,
    HOSTED_ON,
    TelethonLogger,
    where_hosted,
)


try:
    from safety.tools import *
except ImportError:
    KEEP_SAFE, call_back, cleanup_cache = None, None, None
    LOGS.error("'safety' package not found!")
